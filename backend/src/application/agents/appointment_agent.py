class AppointmentAgent:
    """
    Randevu Alma Ajanı (Appointment Agent)
    
    Kullanıcının doktor randevusu alma isteklerini yönetir.
    Dış bir hastane API servisine (HospitalAPIService interface) bağlanarak
    uygun slotları çeker ve randevu oluşturur.
    """
    def __init__(self, hospital_api):
        self.hospital_api = hospital_api
        
    async def handle_appointment_request(self, query: str, user_id: str) -> str:
         # Burada LLM kullanarak hangi branş ve hangi hastane istendiğini parse ederiz.
         # Sonra dış API'den boş randevuları sorgularız.
         slots = await self.hospital_api.get_slots()
         return f"Randevu talebiniz anlaşıldı. Şu an {len(slots)} boş randevumuz var. Lütfen uygun bir tarih seçin."
