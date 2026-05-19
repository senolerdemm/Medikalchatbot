from __future__ import annotations

import argparse
import json
from pathlib import Path


def _looks_like_model_directory(directory: Path) -> bool:
    if not directory.exists() or not directory.is_dir():
        return False
    has_config = (directory / "config.json").exists()
    has_weights = any(directory.glob("*.safetensors")) or any(
        directory.glob("pytorch_model*.bin")
    )
    has_index = (directory / "model.safetensors.index.json").exists()
    return has_config and (has_weights or has_index)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "QLoRA adapter'ı Hugging Face biçimindeki base model ile birleştirip "
            "tam modeli diske yazar."
        )
    )
    parser.add_argument(
        "--base-model-path",
        required=True,
        help="Base model klasörü (config.json ve ağırlık dosyaları içermeli).",
    )
    parser.add_argument(
        "--adapter-path",
        default="/Users/senolerdem/Desktop/MedicalChatbot/backend/model_assets/qlora",
        help="QLoRA adapter klasörü.",
    )
    parser.add_argument(
        "--output-dir",
        default="/Users/senolerdem/Desktop/MedicalChatbot/backend/model_assets/merged-medassist-llama3",
        help="Birleşmiş modelin yazılacağı klasör.",
    )
    parser.add_argument(
        "--device",
        default="auto",
        choices=["auto", "cpu", "cuda", "mps"],
        help="Modelin yükleneceği cihaz.",
    )
    parser.add_argument(
        "--dtype",
        default="auto",
        choices=["auto", "float16", "bfloat16", "float32"],
        help="Base model yüklenirken kullanılacak ağırlık tipi.",
    )
    parser.add_argument(
        "--max-shard-size",
        default="2GB",
        help="Birleşmiş model yazılırken kullanılacak maksimum shard boyutu.",
    )
    return parser.parse_args()


def resolve_device(torch_module, requested: str) -> str:
    if requested != "auto":
        return requested
    if getattr(torch_module.cuda, "is_available", lambda: False)():
        return "cuda"
    if getattr(torch_module.backends, "mps", None) and torch_module.backends.mps.is_available():
        return "mps"
    return "cpu"


def resolve_dtype(torch_module, device: str, requested: str):
    if requested == "float16":
        return torch_module.float16
    if requested == "bfloat16":
        return torch_module.bfloat16
    if requested == "float32":
        return torch_module.float32
    if device == "cuda":
        return torch_module.float16
    if device == "mps":
        return torch_module.float16
    return torch_module.float32


def main() -> int:
    args = parse_args()

    base_model_dir = Path(args.base_model_path).expanduser().resolve()
    adapter_dir = Path(args.adapter_path).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()

    if not _looks_like_model_directory(base_model_dir):
        print(
            "Base model klasörü eksik veya tamamlanmamış.\n"
            f"Kontrol edilen klasör: {base_model_dir}\n"
            "Beklenenler: config.json ve model safetensors/bin dosyaları."
        )
        return 1

    if not (adapter_dir / "adapter_config.json").exists() or not (
        adapter_dir / "adapter_model.safetensors"
    ).exists():
        print(
            "Adapter klasöründe gerekli dosyalar bulunamadı.\n"
            f"Kontrol edilen klasör: {adapter_dir}"
        )
        return 1

    try:
        import torch
        from peft import PeftModel
        from transformers import AutoModelForCausalLM, AutoTokenizer
    except Exception as error:
        print(f"Gerekli kütüphaneler yüklenemedi: {error}")
        return 1

    device = resolve_device(torch, args.device)
    dtype = resolve_dtype(torch, device, args.dtype)

    print(f"Base model yükleniyor: {base_model_dir}")
    tokenizer_source = adapter_dir if (adapter_dir / "tokenizer.json").exists() else base_model_dir
    tokenizer = AutoTokenizer.from_pretrained(str(tokenizer_source), local_files_only=True)
    base_model = AutoModelForCausalLM.from_pretrained(
        str(base_model_dir),
        torch_dtype=dtype,
        local_files_only=True,
    )

    print(f"Adapter ekleniyor: {adapter_dir}")
    model = PeftModel.from_pretrained(
        base_model,
        str(adapter_dir),
        local_files_only=True,
    )

    print("Adapter birleştiriliyor...")
    merged_model = model.merge_and_unload()
    merged_model.to(device)
    merged_model.eval()

    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"Birleşmiş model yazılıyor: {output_dir}")
    merged_model.save_pretrained(
        str(output_dir),
        safe_serialization=True,
        max_shard_size=args.max_shard_size,
    )
    tokenizer.save_pretrained(str(output_dir))

    manifest = {
        "base_model_path": str(base_model_dir),
        "adapter_path": str(adapter_dir),
        "device": device,
        "dtype": str(dtype),
        "merged_output": str(output_dir),
    }
    (output_dir / "merge_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("Tam model başarıyla oluşturuldu.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
