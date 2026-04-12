# Bağımlılık Enjeksiyonu ve Konteynerı (Dependency Injection Container)
# 
# Clean Architecture felsefesine sadık kalmak ve modüler/test edilebilir bir sistem
# geliştirmek adına tüm modüllerimiz bu konteyner üzerinden somutlanacak
# ve istemcilere Interface (Protocol vb.) olarak sunulacak.
#

from functools import lru_cache
from typing import Optional

# Dependency (Portlar / Interfaceler) -> Infrastructure Adapter bağlantıları
from application.orchestrator.agent_orchestrator import AgentOrchestrator
from application.agents.appointment_agent import AppointmentAgent
from application.agents.information_agent import InformationAgent
from application.agents.personal_agent import PersonalAgent

# Gelecekte implemente edilecek port/adapter örnekleri. (Mock)
class DummyLLM:
    async def generate(self, text): return "Merhaba ben AI, şu an test modundayım."

class DummyVectorDB:
    async def similarity_search(self, q, k=3): return []

class DummyHospitalAPI:
    async def get_slots(self): return []

def get_llm_engine():
    return DummyLLM()

def get_vector_db():
    return DummyVectorDB()

def get_hospital_api():
    return DummyHospitalAPI()

@lru_cache()
def get_information_agent() -> InformationAgent:
    """Singleton tarzında InformationAgent'ı enjekte et"""
    vector_db = get_vector_db()
    llm = get_llm_engine()
    return InformationAgent(vector_db=vector_db, llm_engine=llm)

@lru_cache()
def get_appointment_agent() -> AppointmentAgent:
     """Singleton tarzında AppointmentAgent'ı enjekte et"""
     hospital_api = get_hospital_api()
     return AppointmentAgent(hospital_api=hospital_api)

@lru_cache()
def get_personal_agent() -> PersonalAgent:
     """Singleton tarzında PersonalAgent'ı enjekte et"""
     return PersonalAgent()

@lru_cache()
def get_agent_orchestrator() -> AgentOrchestrator:
     """Anaorkestratörü enjekte etip döndür."""
     info_agent = get_information_agent()
     appt_agent = get_appointment_agent()
     pers_agent = get_personal_agent()
     llm_engine = get_llm_engine()
     return AgentOrchestrator(
          information_agent=info_agent,
          appointment_agent=appt_agent,
          personal_agent=pers_agent,
          llm_engine=llm_engine
     )
