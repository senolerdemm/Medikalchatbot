class PersonalAgent:
    """
    Kişisel Asistan Ajanı (Personal Agent)
    
    Kullanıcının geçmişteki hastalık kayıtları, geçirdiği operasyonlar
    ve tahlil sonuçları (UserHistoryRepository interface) hakkında
    sorular sorulduğunda devreye giren ajandır.
    """
    def __init__(self):
        # Gerçek uygulamada self.user_repo gibi bir bağımlılıkla başlatılır
        pass
        
    async def handle_history_query(self, query: str, user_id: str) -> str:
        # Repository'den (PostgreSQL vb.) geçmiş verileri getir.
        # RAG'a benzer şekilde prompt oluşturup LLM ile geçmişini özetler.
        return "Sistemde yer alan sağlık geçmişinize göre son tahlilleriniz normal görünmektedir."
