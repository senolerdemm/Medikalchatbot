from __future__ import annotations

import asyncio
import json
import re
from collections.abc import Sequence
from json import JSONDecodeError
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from core.config import get_settings
from domain.entities.health_query import RetrievedDocument
from domain.ports.ai.llm_engine import LLMEngine


class Llama3QLoRAClient(LLMEngine):
    """
    Varsayılan olarak Ollama üzerinden yerel Llama 3 çağırır.

    İstenirse aynı arayüz üzerinden Hugging Face tabanlı base model + PEFT
    adapter kombinasyonunu da yükleyebilir. Böylece plain llama3 ile eğitilmiş
    QLoRA adapter arasında sadece konfigürasyon değiştirerek geçiş yapılabilir.
    """

    def __init__(self) -> None:
        self.settings = get_settings()
        self._local_bundle: tuple[Any, Any, str] | None = None

    async def warm_up(self) -> None:
        """Load the Ollama model before the first user-facing chat request."""
        if self.settings.llm_provider.lower() != "ollama":
            return

        payload = {
            "model": self.settings.llm_model,
            "stream": False,
            "keep_alive": self.settings.llm_keep_alive,
            "messages": [
                {
                    "role": "system",
                    "content": "Yalnızca hazırlanıyorum yanıtı ver.",
                },
                {"role": "user", "content": "hazirlik"},
            ],
            "options": {
                "temperature": 0.0,
                "num_predict": 1,
                "num_ctx": 512,
            },
        }
        try:
            await asyncio.to_thread(self._post_json, "/api/chat", payload)
        except RuntimeError:
            return

    async def generate_response(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        context_documents: Sequence[RetrievedDocument] | None = None,
    ) -> str:
        try:
            response = await self._chat(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                context_documents=context_documents,
            )
            content = response.get("message", {}).get("content", "").strip()
            if content:
                return self._sanitize_text_response(content)
        except RuntimeError:
            pass

        return self._fallback_response(
            user_prompt=user_prompt,
            context_documents=context_documents,
        )

    async def generate_structured_output(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        schema_hint: str,
        context_documents: Sequence[RetrievedDocument] | None = None,
    ) -> dict[str, Any] | None:
        try:
            response = await self._chat(
                system_prompt=system_prompt,
                user_prompt=(
                    f"{user_prompt}\n\n"
                    "Yanıtını yalnızca geçerli bir JSON nesnesi olarak döndür.\n"
                    f"Beklenen şema:\n{schema_hint}"
                ),
                context_documents=context_documents,
                response_format="json",
                temperature=0.0,
            )
            content = response.get("message", {}).get("content", "").strip()
            if not content:
                return None
            parsed = self._parse_json_object(content)
            return parsed if isinstance(parsed, dict) else None
        except RuntimeError:
            return None

    async def _chat(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        context_documents: Sequence[RetrievedDocument] | None = None,
        response_format: str | None = None,
        temperature: float | None = None,
    ) -> dict[str, Any]:
        provider = self.settings.llm_provider.lower()
        if provider == "hf_adapter":
            return await asyncio.to_thread(
                self._chat_hf_adapter,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                context_documents=context_documents,
                temperature=temperature,
            )
        if provider == "hf_local":
            return await asyncio.to_thread(
                self._chat_hf_local,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                context_documents=context_documents,
                temperature=temperature,
            )

        payload = {
            "model": self.settings.llm_model,
            "stream": False,
            "keep_alive": self.settings.llm_keep_alive,
            "messages": [
                {"role": "system", "content": self._with_response_rules(system_prompt)},
                {
                    "role": "user",
                    "content": self._build_user_prompt(
                        user_prompt=user_prompt,
                        context_documents=context_documents,
                    ),
                },
            ],
            "options": {
                "temperature": (
                    self.settings.llm_temperature
                    if temperature is None
                    else temperature
                ),
                "num_predict": self.settings.llm_max_new_tokens,
                "num_ctx": self.settings.llm_context_window,
            },
        }
        if response_format is not None:
            payload["format"] = response_format

        return await asyncio.to_thread(self._post_json, "/api/chat", payload)

    def _with_response_rules(self, system_prompt: str) -> str:
        return (
            f"{system_prompt.strip()}\n\n"
            "Yanıt kuralları: Forum tarihi, kullanıcı adı, yıldızlı ayraç, "
            "'cevaplandı' gibi veri seti kalıntıları yazma. "
            "Sadece nihai Türkçe cevabı ver."
        )

    def _sanitize_text_response(self, text: str) -> str:
        cleaned = text.strip()
        answer_marker = re.search(r"(?im)^\s*#{0,3}\s*Cevap\s*:?\s*$", cleaned)
        if answer_marker:
            cleaned = cleaned[answer_marker.end() :].strip()

        artifact_patterns = (
            r"(?im)^\s*\d+\s+(?:saniye|dakika|saat|gün|gun|hafta|ay|yıl|yil)\s+önce\s*$",
            r"(?im)^\s*[*\s]+\d{1,2}:\d{2}:\d{2}\s+tarihinde\s+cevaplandı\s*$",
            r"(?im)^\s*.*\bsoruyu\s+cevapladı\b.*$",
            r"(?im)^\s*.*\bcevaplandı\s*$",
            r"(?im)^\s*.*\bcevaplandırıldığını\b.*$",
            r"(?im)^\s*sayfa\s*:\s*\d+\s*$",
            r"(?im)^\s*öz?et\s*:\s*.*$",
            r"(?im)^\s*#{1,6}\s*(?:cevap|cevap bilgisi|soru|yanıt)\s*:?\s*$",
        )
        for pattern in artifact_patterns:
            cleaned = re.sub(pattern, "", cleaned).strip()

        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
        return cleaned or text.strip()

    def _chat_hf_adapter(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        context_documents: Sequence[RetrievedDocument] | None = None,
        temperature: float | None = None,
    ) -> dict[str, Any]:
        tokenizer, model, device = self._get_adapter_bundle()
        return self._generate_hf_response(
            tokenizer=tokenizer,
            model=model,
            device=device,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            context_documents=context_documents,
            temperature=temperature,
        )

    def _chat_hf_local(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        context_documents: Sequence[RetrievedDocument] | None = None,
        temperature: float | None = None,
    ) -> dict[str, Any]:
        tokenizer, model, device = self._get_hf_local_bundle()
        return self._generate_hf_response(
            tokenizer=tokenizer,
            model=model,
            device=device,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            context_documents=context_documents,
            temperature=temperature,
        )

    def _generate_hf_response(
        self,
        *,
        tokenizer: Any,
        model: Any,
        device: str,
        system_prompt: str,
        user_prompt: str,
        context_documents: Sequence[RetrievedDocument] | None = None,
        temperature: float | None = None,
    ) -> dict[str, Any]:
        prompt_text = self._build_user_prompt(
            user_prompt=user_prompt,
            context_documents=context_documents,
        )
        messages = [
            {"role": "system", "content": self._with_response_rules(system_prompt)},
            {"role": "user", "content": prompt_text},
        ]
        if hasattr(tokenizer, "apply_chat_template"):
            rendered_prompt = tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True,
            )
        else:
            rendered_prompt = (
                f"Sistem:\n{self._with_response_rules(system_prompt)}\n\n"
                f"Kullanıcı:\n{prompt_text}\n\n"
                "Asistan:\n"
            )

        inputs = tokenizer(rendered_prompt, return_tensors="pt")
        inputs = {
            key: value.to(device)
            for key, value in inputs.items()
        }
        effective_temperature = (
            self.settings.llm_temperature if temperature is None else temperature
        )
        generation_kwargs = {
            "max_new_tokens": self.settings.llm_max_new_tokens,
            "pad_token_id": tokenizer.eos_token_id,
            "eos_token_id": tokenizer.eos_token_id,
        }
        if effective_temperature <= 0:
            generation_kwargs["do_sample"] = False
        else:
            generation_kwargs["do_sample"] = True
            generation_kwargs["temperature"] = effective_temperature
            generation_kwargs["top_p"] = 0.95

        output_ids = model.generate(
            **inputs,
            **generation_kwargs,
        )
        generated_ids = output_ids[0][inputs["input_ids"].shape[1] :]
        content = tokenizer.decode(
            generated_ids,
            skip_special_tokens=True,
        ).strip()
        return {"message": {"content": content}}

    def _get_adapter_bundle(self) -> tuple[Any, Any, str]:
        if self._local_bundle is not None:
            return self._local_bundle

        adapter_path = self.settings.llm_adapter_path
        if not adapter_path:
            raise RuntimeError(
                "HF adapter modu için LLM_ADAPTER_PATH ayarı gereklidir."
            )

        adapter_dir = Path(adapter_path)
        if not adapter_dir.exists():
            raise RuntimeError(
                f"Adapter klasörü bulunamadı: {adapter_dir}"
            )

        try:
            import torch
            from peft import PeftModel
            from transformers import AutoModelForCausalLM, AutoTokenizer
        except Exception as error:  # pragma: no cover - env bağımlı
            raise RuntimeError(
                "HF adapter modu için transformers, torch ve peft kurulmalı."
            ) from error

        base_model_name_or_path = self._resolve_base_model_name(adapter_dir)
        self._validate_base_model_source(base_model_name_or_path)
        tokenizer_source = str(adapter_dir) if (adapter_dir / "tokenizer.json").exists() else base_model_name_or_path
        device = self._resolve_device(torch)
        dtype = self._resolve_dtype(torch, device)

        try:
            tokenizer = AutoTokenizer.from_pretrained(
                tokenizer_source,
                local_files_only=True,
            )
            base_model = AutoModelForCausalLM.from_pretrained(
                base_model_name_or_path,
                torch_dtype=dtype,
                local_files_only=True,
            )
            model = PeftModel.from_pretrained(
                base_model,
                str(adapter_dir),
                local_files_only=True,
            )
            if hasattr(model, "merge_and_unload"):
                model = model.merge_and_unload()
            model.to(device)
            model.eval()
        except Exception as error:  # pragma: no cover - local model env bağımlı
            raise RuntimeError(
                "HF adapter modeli yüklenemedi. Base model yerelde mevcut değilse "
                "LLM_BASE_MODEL_PATH ayarlayın veya Hugging Face cache'ini doğrulayın."
            ) from error

        self._local_bundle = (tokenizer, model, device)
        return self._local_bundle

    def _get_hf_local_bundle(self) -> tuple[Any, Any, str]:
        if self._local_bundle is not None:
            return self._local_bundle

        model_path = self.settings.llm_base_model_path
        if not model_path:
            raise RuntimeError(
                "hf_local modu için LLM_BASE_MODEL_PATH ayarı gereklidir."
            )

        model_dir = Path(model_path)
        self._validate_base_model_source(str(model_dir))

        try:
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer
        except Exception as error:  # pragma: no cover - env bağımlı
            raise RuntimeError(
                "hf_local modu için transformers ve torch kurulmalı."
            ) from error

        device = self._resolve_device(torch)
        dtype = self._resolve_dtype(torch, device)
        try:
            tokenizer = AutoTokenizer.from_pretrained(
                str(model_dir),
                local_files_only=True,
            )
            model = AutoModelForCausalLM.from_pretrained(
                str(model_dir),
                torch_dtype=dtype,
                local_files_only=True,
            )
            model.to(device)
            model.eval()
        except Exception as error:  # pragma: no cover - local model env bağımlı
            raise RuntimeError(
                "Yerel HF model klasörü yüklenemedi. Model dosyalarını doğrulayın."
            ) from error

        self._local_bundle = (tokenizer, model, device)
        return self._local_bundle

    def _validate_base_model_source(self, base_model_name_or_path: str) -> None:
        candidate = Path(base_model_name_or_path)
        if not candidate.exists():
            return
        if not candidate.is_dir():
            raise RuntimeError(
                f"Base model yolu klasör değil: {candidate}"
            )
        has_config = (candidate / "config.json").exists()
        has_weights = any(candidate.glob("*.safetensors")) or any(
            candidate.glob("pytorch_model*.bin")
        ) or (candidate / "model.safetensors.index.json").exists()
        if not (has_config and has_weights):
            raise RuntimeError(
                "Base model klasörü bulundu ancak model ağırlıkları eksik görünüyor. "
                f"Kontrol edilen klasör: {candidate}"
            )

    def _resolve_base_model_name(self, adapter_dir: Path) -> str:
        if self.settings.llm_base_model_path:
            return self.settings.llm_base_model_path
        adapter_config = adapter_dir / "adapter_config.json"
        if not adapter_config.exists():
            raise RuntimeError(
                "Adapter klasöründe adapter_config.json bulunamadı."
            )
        payload = json.loads(adapter_config.read_text(encoding="utf-8"))
        base_model_name = payload.get("base_model_name_or_path")
        if not isinstance(base_model_name, str) or not base_model_name.strip():
            raise RuntimeError(
                "adapter_config.json içinde base_model_name_or_path bulunamadı."
            )
        return base_model_name

    def _resolve_device(self, torch_module: Any) -> str:
        configured = self.settings.llm_device.lower()
        if configured != "auto":
            return configured
        if torch_module.cuda.is_available():
            return "cuda"
        mps = getattr(torch_module.backends, "mps", None)
        if mps is not None and mps.is_available():
            return "mps"
        return "cpu"

    def _resolve_dtype(self, torch_module: Any, device: str):
        if device == "cpu":
            return torch_module.float32
        return torch_module.float16

    def _post_json(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.settings.llm_base_url.rstrip('/')}{path}"
        request = Request(
            url=url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.settings.llm_timeout_seconds) as response:
                raw_body = response.read().decode("utf-8")
                return json.loads(raw_body)
        except (HTTPError, URLError, TimeoutError, JSONDecodeError, OSError) as error:
            raise RuntimeError(
                f"Ollama isteği başarısız oldu: {error}"
            ) from error

    def _build_user_prompt(
        self,
        *,
        user_prompt: str,
        context_documents: Sequence[RetrievedDocument] | None = None,
    ) -> str:
        if not context_documents:
            return user_prompt

        context_blocks = [
            (
                f"Belge {index + 1}\n"
                f"Başlık: {document.title}\n"
                f"Kaynak: {document.source}\n"
                f"İçerik: {document.content}"
            )
            for index, document in enumerate(context_documents)
        ]
        return (
            "Bağlam belgeleri:\n"
            f"{'\n\n'.join(context_blocks)}\n\n"
            f"Görev:\n{user_prompt}"
        )

    def _parse_json_object(self, text: str) -> dict[str, Any] | None:
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.removeprefix("```json").removeprefix("```").strip()
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3].strip()

        try:
            parsed = json.loads(cleaned)
            return parsed if isinstance(parsed, dict) else None
        except JSONDecodeError:
            start = cleaned.find("{")
            end = cleaned.rfind("}")
            if start == -1 or end == -1 or end <= start:
                return None
            try:
                parsed = json.loads(cleaned[start : end + 1])
            except JSONDecodeError:
                return None
            return parsed if isinstance(parsed, dict) else None

    def _fallback_response(
        self,
        *,
        user_prompt: str,
        context_documents: Sequence[RetrievedDocument] | None = None,
    ) -> str:
        if context_documents:
            best_doc = context_documents[0]
            return (
                "Llama 3 servisine ulaşılamadığı için bağlamdan güvenli bir özet "
                f"sunuyorum: {best_doc.excerpt(220)} "
                "Bu yanıt tanı yerine geçmez; belirtileriniz artarsa doktor "
                "değerlendirmesi alın."
            )

        if "Hasta profili:" in user_prompt:
            lines = [line.strip() for line in user_prompt.splitlines() if line.strip()]
            profile_line = next(
                (line for line in lines if line.startswith("Hasta profili:")),
                "",
            )
            history_lines = [line for line in lines if line.startswith("- ")]
            summary = (
                profile_line.replace("Hasta profili:", "").strip()
                or "Profil bilgisi yok."
            )
            recent = (
                " ".join(history_lines[:2])
                if history_lines
                else "Yakın tarihli kayıt bulunamadı."
            )
            return (
                f"Kişisel kayıtlarınıza göre özet: {summary}. "
                f"Son veriler: {recent} "
                "Bu bilgiler tanı yerine geçmez; yeni veya artan şikayetlerde "
                "doktorunuza başvurun."
            )

        return (
            "Şu an Llama 3 servisine erişemiyorum. Bu nedenle yalnızca genel "
            "yönlendirme verebiliyorum. Semptomlarınız şiddetliyse veya ani "
            "geliştiyse profesyonel sağlık desteği almanız gerekir."
        )
