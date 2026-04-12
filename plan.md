# KAPSAMLI SİSTEM MİMARİSİ VE KOD OLUŞTURMA GÖREVİ (CLEAN ARCHITECTURE & DDD)

Sen kıdemli bir yazılım mimarısın. "Türkçe Doğal Dil Destekli Akıllı Tıbbi Asistan" (Turkish Language Based Smart Medical Assistant) projesinin temel iskeletini (boilerplate) oluşturmanı istiyorum. 

Sistem; Flutter tabanlı bir mobil uygulama ve arka planda çalışan, LLaMA-3 (QLoRA) ve RAG mimarisiyle desteklenen, ajan tabanlı (Agent-based) bir FastAPI (Python) sunucusundan oluşmaktadır.

Projeyi kesinlikle **Clean Architecture** ve **Domain-Driven Design (DDD)** prensiplerine uygun olarak inşa etmelisin. Spagetti kod istemiyorum; bağımlılıkların içe doğru (Domain'e) aktığı, Dependency Injection kullanılan, katmanlı bir yapı kurmalısın.

## 1. BACKEND MİMARİSİ (FastAPI - Python)

Backend sistemi bir "AI Agent API"dir. Lütfen aşağıdaki DDD katmanlarına uygun klasör yapısını ve temel dosyaları (içleri açıklayıcı yorum satırları ve interface/soyut sınıf tanımlarıyla dolu olacak şekilde) oluştur.

### 1.1. Domain Layer (Çekirdek - Dış bağımlılık SIFIR)
Burada sistemin ana varlıkları (Entities) ve arayüzleri (Interfaces/Ports) yer almalı.
* `domain/entities/patient.py`
* `domain/entities/health_query.py`
* `domain/entities/appointment.py`
* `domain/ports/repositories/user_history_repository.py` (Interface)
* `domain/ports/services/hospital_api_service.py` (Interface)
* `domain/ports/ai/llm_engine.py` (Interface)
* `domain/ports/ai/vector_db_service.py` (Interface - RAG için)

### 1.2. Application Layer (Use Cases & Agents)
İş kurallarının (Business Rules) ve Ajan mantığının (Orchestration) çalıştığı yer. C3 ve C4 diyagramlarındaki ajanları buraya Use Case / Service olarak yedir.
* `application/use_cases/process_medical_query.py`
* `application/use_cases/book_hospital_appointment.py`
* `application/orchestrator/agent_orchestrator.py` (Gelen isteğin niyetini anlayıp ilgili ajana yönlendiren ana mantık)
* `application/agents/information_agent.py` (RAG ve LLM portlarını kullanarak sağlık sorusunu yanıtlar)
* `application/agents/appointment_agent.py` (Hastane API portunu kullanarak randevu alır)
* `application/agents/personal_agent.py` (Kullanıcı geçmişini analiz eder)

### 1.3. Infrastructure Layer (Dış Dünya Entegrasyonları)
Domain katmanındaki Interface'lerin (Portların) somut (concrete) implementasyonları (Adapterlar).
* `infrastructure/database/postgres/user_history_db.py` (SQLAlchemy/SQLModel ile PostgreSQL bağlantısı)
* `infrastructure/database/vector/faiss_chroma_db.py` (RAG için tıbbi embedding'leri tutan yapı)
* `infrastructure/external_api/hospital_mock_api.py` (Simüle edilmiş randevu sistemi)
* `infrastructure/ai/llama3_qlora_client.py` (LLM Engine implementasyonu)
* `infrastructure/ai/embedding_service.py` (Metinleri vektör uzayına çeviren servis)

### 1.4. Presentation Layer (API Controllers)
FastAPI router'ları, Pydantic şemaları (DTOs) ve Dependency Injection container'ı.
* `presentation/api/controllers/chat_controller.py` (Mobil uygulamadan gelen istekleri karşılar)
* `presentation/api/schemas/requests.py`
* `presentation/api/schemas/responses.py`
* `presentation/dependencies.py` (Portlar ile Infrastructure implementasyonlarını birbirine bağlayan DI Container)
* `main.py` (FastAPI app factory)


## 2. FRONTEND MİMARİSİ (Flutter - Dart)

Flutter uygulamasını da BLoC/Cubit veya Riverpod (hangisini tercih edersen) state management çözümüyle Clean Architecture yapısında kur. 

### 2.1. Domain Layer
* `lib/domain/entities/message.dart`
* `lib/domain/entities/appointment_slot.dart`
* `lib/domain/repositories/chat_repository.dart` (Abstract class)

### 2.2. Data Layer
* `lib/data/models/message_model.dart`
* `lib/data/datasources/remote/fastapi_client.dart` (Dio veya Http ile Python backend'e bağlanacak)
* `lib/data/repositories/chat_repository_impl.dart`

### 2.3. Presentation Layer
Sunumda belirtilen ekranları içermelidir:
* `lib/presentation/screens/input_screen.dart` (Karşılama ve ilk veri girişi)
* `lib/presentation/screens/chat_screen.dart` (Ajanlarla konuşma alanı)
* `lib/presentation/screens/result_screen.dart` (Randevu/Analiz sonucu)
* `lib/presentation/blocs/chat_bloc.dart` (İş mantığını UI'dan ayıran state yöneticisi)

## Çıktı Beklentisi:
Lütfen bana tüm bu yapıyı bir ağaç (tree) görünümünde özetle. Ardından, en kritik 3 dosyanın (Örn: `agent_orchestrator.py`, `information_agent.py` ve `main.py` Dependency Injection kısmı) detaylı, yoruma dayalı iskelet kodlarını yazarak başla.