from typing import Optional, Dict, Any

class AgentOrchestrator:
    """
    Agent Orchestrator
    
    Bu sınıf, kullanıcıdan gelen doğal dil sorgularının niyetini (intent) analiz eder
    ve isteği ilgili uzman ajana (InformationAgent, AppointmentAgent veya PersonalAgent) yönlendirir.
    
    Domain-Driven Design (DDD) ve Clean Architecture prensiplerine uygun olarak,
    tüm bağımlılıklar (ajanlar ve dış servisler) kurgulama (Dependency Injection) aşamasında
    enjekte edilmelidir.
    """
    
    def __init__(
        self,
        information_agent: Any,  # İlgili interface/sınıftan türetilmiş nesneler gelmeli
        appointment_agent: Any,
        personal_agent: Any,
        llm_engine: Any          # Sorgunun niyetini (intent) anlamak için LLM motoru portu
    ):
        self.information_agent = information_agent
        self.appointment_agent = appointment_agent
        self.personal_agent = personal_agent
        self.llm_engine = llm_engine

    async def process_query(self, query_text: str, user_id: str) -> Dict[str, Any]:
        """
        Kullanıcıdan gelen sorguyu ilgili ajana yönlendirip sonucu döndürür.
        """
        # 1. Intent Analysis (Niyet Analizi)
        # LLM motorunu kullanarak metnin amacını belirleriz (Örn: "randevu", "bilgi", "gecmis")
        intent = await self._analyze_intent(query_text)
        
        # 2. İlgili Ajanı Çağırma
        if intent == "appointment":
             # Randevu alma işlemini yönetecek ajana yönlendir
            response = await self.appointment_agent.handle_appointment_request(query_text, user_id)
            source = "Appointment Agent"
            
        elif intent == "personal_history":
             # Kişisel sağlık geçmişi ve önceki kayıtlarla ilgili soruları yanıtlayacak ajan
            response = await self.personal_agent.handle_history_query(query_text, user_id)
            source = "Personal Agent"
            
        else:
             # Genel tıbbi bilgi (RAG kullanarak) arayan soruları yanıtlayacak ajan
            response = await self.information_agent.answer_medical_query(query_text)
            source = "Information Agent"

        return {
            "status": "success",
            "message": response,
            "handled_by": source,
            "detected_intent": intent
        }
        
    async def _analyze_intent(self, query_text: str) -> str:
        """
        Gelen metnin niyetini analiz kuralı veya LLM portu ile belirler.
        (Şimdilik basit bir kural tabanlı mock implementasyon)
        """
        query_lower = query_text.lower()
        if "randevu" in query_lower or "almak istiyorum" in query_lower or "doktor" in query_lower:
            return "appointment"
        elif "benim" in query_lower or "önceki" in query_lower or "tahlil" in query_lower:
            return "personal_history"
        else:
            return "information"
