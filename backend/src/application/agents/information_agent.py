class InformationAgent:
    """
    Tıbbi Bilgi Ajanı (Information Agent)

    Kullanıcıdan gelen genel sağlık ve hastalık sorularını (örneğin "Baş ağrısına ne iyi gelir?",
    "Diyabetin belirtileri nelerdir?") yanıtlamaktan sorumludur.
    RAG (Retrieval-Augmented Generation) mimarisini kullanarak:
    - Vektör veritabanından (örneğin sağlık makaleleri, güvenilir kaynaklar) en uygun bilgileri getirir,
    - Arama sonuçlarını ve kullanıcı sorusunu LLM motoruna besleyip uygun dilde metin üretimi sağlar.

    Bağımlılıklar (Dependency Injection aracılığıyla enjekte edici katmanlar):
    - vector_db (VectorDBService interface implementation): İçeriği getirecek servis
    - llm_engine (LLMEngine interface implementation): Metni üretecek temel motor 
    """

    def __init__(self, vector_db, llm_engine):
        self.vector_db = vector_db
        self.llm_engine = llm_engine

    async def answer_medical_query(self, query: str) -> str:
        """
        Sorguya (query) göre veritabanından uygun bağlamı çeker ve LLM vasıtasıyla yanıtlar.
        """
        # 1. Bağlamı çek (Retrieval)
        context_docs = await self.vector_db.similarity_search(query, k=3)
        
        # 2. Seçilen dökümanları tek bir string bağlamında birleştir
        context_text = "\n".join([doc.page_content for doc in context_docs]) if context_docs else ""

        # 3. Prompt oluştur (Prompt Engineering)
        prompt = f"""
        Sen "Türkçe Doğal Dil Destekli Akıllı Tıbbi Asistan"sın. Lütfen sadece sağlanan tıbbi bağlama dayanarak yanıt ver.
        Eğer sorunun yanıtı bağlamda yoksa uydurma, "Bu konuda yeterli bilgiye sahip değilim" de.
        
        Bağlam:
        {context_text}
        
        Kullanıcı Sorusu:
        {query}
        
        Yanıt:
        """

        # 4. Yanıt Üretimi (Generation)
        response = await self.llm_engine.generate(prompt)
        
        return response
