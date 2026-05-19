# C4 Mermaid Diyagramları

Bu doküman mevcut kod yapısına göre hazırlanmıştır. Diyagramlar `backend/src` ve `frontend/lib` altındaki gerçek sınıf, controller, agent ve repository bağlantılarını temel alır.

## 1. C4 Context Diagram

```mermaid
C4Context
    title Türkçe Dil Tabanlı Akıllı Tıbbi Asistan - Sistem Bağlamı

    Person(patient, "Hasta / Kullanıcı", "Mobil uygulama üzerinden sağlık sorusu sorar, geçmişini görüntüler ve randevu işlemleri yapar.")
    System(mobile_app, "Mobil Uygulama", "Flutter istemci. Chat, geçmiş özeti ve randevu ekranlarını sunar.")
    System(ai_api, "AI Agent API", "FastAPI backend. Auth, chat orchestration, agent routing, RAG ve randevu işlemlerini yürütür.")

    SystemDb(postgres, "PostgreSQL", "Kullanıcı, oturum, konuşma, mesaj, hasta geçmişi ve randevu kayıtları.")
    SystemDb(vector_store, "Vector DB / RAG Store", "FAISS IndexFlatIP ve chunks.parquet artefactleri. Chroma yalnızca fallback/cache rolündedir.")
    System_Ext(llm_runtime, "LLM Runtime", "Ollama veya HF local adapter. Llama 3 / QLoRA fine-tuned model cevap, intent ve özet üretir.")
    System_Ext(hospital_provider, "Hospital Provider", "Şu an gerçekçi mock servis. Slot arama, rezervasyon, iptal ve listeleme portunu temsil eder.")
    System_Ext(model_assets, "Model ve RAG Artefactleri", "Base Llama 3, QLoRA adapter, merged model ve rapordaki RAG çıktı dosyaları.")

    Rel(patient, mobile_app, "Kullanır", "UI")
    Rel(mobile_app, ai_api, "API çağrısı yapar", "HTTP/JSON, Bearer session token")
    Rel(ai_api, postgres, "Operasyonel veriyi okur/yazar", "SQLAlchemy")
    Rel(ai_api, vector_store, "Benzer tıbbi bağlam arar", "embedding + similarity search")
    Rel(ai_api, llm_runtime, "Prompt gönderir, metin/JSON yanıt alır", "Ollama API veya local Transformers")
    Rel(ai_api, hospital_provider, "Slot arar, randevu alır/iptal eder", "HospitalAPIService portu")
    Rel(model_assets, llm_runtime, "Model ağırlığı ve adapter sağlar", "local filesystem")
    Rel(model_assets, vector_store, "RAG index/chunk verisi sağlar", "local filesystem")

    UpdateRelStyle(patient, mobile_app, $textColor="green", $lineColor="green")
    UpdateRelStyle(mobile_app, ai_api, $textColor="green", $lineColor="green")
```

## 2. C4 Container Diagram

```mermaid
C4Container
    title Türkçe Dil Tabanlı Akıllı Tıbbi Asistan - Container Diyagramı

    Person(patient, "Hasta / Kullanıcı", "Chat ve randevu akışlarını başlatır.")

    System_Boundary(system, "Türkçe Dil Tabanlı Akıllı Tıbbi Asistan") {
        Container(flutter_ui, "Flutter Mobile App", "Dart / Flutter", "Onboarding, login, chat, geçmiş özeti, randevu merkezi ve sonuç ekranları.")
        Container(fastapi, "AI Agent API", "Python / FastAPI", "HTTP endpointleri, dependency wiring, use-case orchestration ve agent response sözleşmesi.")
        Container(app_layer, "Application Layer", "Python", "ProcessMedicalQueryUseCase, AgentOrchestrator, IntentClassifier ve üç agent.")
        Container(domain_layer, "Domain Layer", "Python dataclass + port interfaces", "HealthQuery, PatientProfile, AppointmentSlot, repository/service portları.")
        Container(infra_layer, "Infrastructure Layer", "Python adapters", "PostgreSQL repository, FAISS birincil vector adapter, Llama3 client ve HospitalMockAPI.")
        ContainerDb(postgres, "PostgreSQL", "postgres:16", "users, user_sessions, patient_profiles, patient_history_entries, conversations, messages, appointments.")
        ContainerDb(vector_store, "Vector Store", "FAISS IndexFlatIP + chunks.parquet", "Tıbbi makale chunkları, metadata ve 768 boyutlu mpnet embedding indexi.")
        Container(llm_runtime, "LLM Runtime", "Ollama / Transformers / PEFT", "Llama 3 veya QLoRA adapterlı modelle metin ve JSON üretimi.")
        Container(hospital_mock, "Hospital Mock Provider", "Python in-memory adapter", "Çok şehirli, çok branşlı slot havuzu ve mock booking state.")
    }

    Rel(patient, flutter_ui, "Kullanır")
    Rel(flutter_ui, fastapi, "Auth, chat ve appointment çağrıları", "HTTP/JSON")
    Rel(fastapi, app_layer, "Use-case çağırır", "Python DI")
    Rel(app_layer, domain_layer, "Entity ve port kullanır")
    Rel(app_layer, infra_layer, "Port implementasyonlarını kullanır")
    Rel(infra_layer, postgres, "Okur/yazar", "SQLAlchemy")
    Rel(infra_layer, vector_store, "Benzerlik araması yapar", "FAISS IndexFlatIP")
    Rel(infra_layer, llm_runtime, "Prompt gönderir", "Ollama API veya local model")
    Rel(infra_layer, hospital_mock, "Slot/booking işlemleri", "HospitalAPIService")

    UpdateLayoutConfig($c4ShapeInRow="3", $c4BoundaryInRow="1")
```

## 3. C4 Component Diagram - Backend

```mermaid
C4Component
    title Backend Component Diyagramı - FastAPI ve Agent Katmanı

    Container_Boundary(api, "AI Agent API / backend/src") {
        Component(auth_controller, "AuthController", "FastAPI router", "POST /auth/login, POST /auth/register, POST /auth/logout, GET /auth/me.")
        Component(chat_controller, "ChatController", "FastAPI router", "POST /chat ve GET /health endpointleri.")
        Component(appointment_controller, "AppointmentController", "FastAPI router", "GET /appointments, POST /appointments/search, book, cancel.")
        Component(dependencies, "Dependency Provider", "presentation/dependencies.py", "Repository, service, agent ve use-case nesnelerini bağlar.")

        Component(process_query, "ProcessMedicalQueryUseCase", "Application use-case", "Conversation oluşturur, HealthQuery üretir, orchestrator sonucu sonrası mesajları kaydeder.")
        Component(orchestrator, "AgentOrchestrator", "Application component", "Intent sonucuna göre Bilgi, Randevu veya Kişisel Geçmiş ajanına yönlendirir.")
        Component(intent, "IntentClassifier", "Rule + LLM classifier", "information, appointment, personal_history kararını verir.")

        Component(info_agent, "Bilgi Ajanı", "InformationAgent", "RAGService ile kaynak getirir, LLM ile Türkçe medikal bilgi cevabı üretir.")
        Component(appointment_agent, "Randevu Ajanı", "AppointmentAgent", "Tercih çıkarır, slot arar, rezervasyon/iptal/listeleme payloadı döner.")
        Component(personal_agent, "Kişisel Geçmiş Ajanı", "PersonalAgent", "Profil, klinik kayıt, randevu ve son mesajları özetler.")

        Component(rag_service, "RAGService", "Application service", "Vector sonuçlarını skor/kelime örtüşmesiyle yeniden sıralar ve filtreler.")
        Component(symptom_guidance, "SymptomGuidanceService", "Application service", "Semptomdan uzmanlık ipucu, alternatif bölüm ve kırmızı bayrak üretir.")
        Component(appointment_service, "AppointmentService", "Application service", "Slot arama fallbackleri, rezervasyon seçimi ve cancellation mantığı.")
        Component(auth_service, "AuthService", "Application service", "E-posta/şifre login, register, logout ve session doğrulama.")
    }

    ContainerDb(postgres, "PostgreSQL", "Operational DB", "Kullanıcı, oturum, profil, geçmiş, konuşma, mesaj ve randevu tabloları.")
    ContainerDb(vector_store, "Vector DB", "FAISS IndexFlatIP + chunks.parquet", "Tıbbi doküman chunkları ve metadata.")
    System_Ext(llm_runtime, "LLM Runtime", "Ollama / HF local / QLoRA", "Metin üretimi, yapılandırılmış JSON ve sohbet özeti.")
    System_Ext(hospital_provider, "Hospital Provider", "HospitalMockAPI", "Slot arama, book_slot, cancel_booking.")

    Rel(auth_controller, auth_service, "Kullanır")
    Rel(chat_controller, process_query, "Kullanır")
    Rel(appointment_controller, appointment_service, "Kullanır")
    Rel(dependencies, auth_controller, "Bağlar")
    Rel(dependencies, chat_controller, "Bağlar")
    Rel(dependencies, appointment_controller, "Bağlar")

    Rel(process_query, orchestrator, "process_query çağırır")
    Rel(process_query, postgres, "conversation + messages kaydeder", "PostgresUserHistoryRepository")
    Rel(orchestrator, intent, "Intent sınıflandırır")
    Rel(orchestrator, info_agent, "information intent")
    Rel(orchestrator, appointment_agent, "appointment intent")
    Rel(orchestrator, personal_agent, "personal_history intent")

    Rel(intent, llm_runtime, "Belirsiz intent için JSON ister")
    Rel(intent, postgres, "Yakın konuşma bağlamı okur")
    Rel(info_agent, rag_service, "retrieve")
    Rel(info_agent, symptom_guidance, "Semptom/branş ipucu")
    Rel(info_agent, llm_runtime, "Kaynaklı cevap üretir")
    Rel(rag_service, vector_store, "similarity_search")

    Rel(appointment_agent, appointment_service, "search/book/cancel/list")
    Rel(appointment_agent, symptom_guidance, "Semptomdan branş çıkarır")
    Rel(appointment_agent, llm_runtime, "Randevu parametresi JSON çıkarır")
    Rel(appointment_agent, postgres, "Son mesaj ve profil okur")
    Rel(appointment_service, hospital_provider, "Slot ve mock rezervasyon")
    Rel(appointment_service, postgres, "Kalıcı booking kaydı")

    Rel(personal_agent, postgres, "Profil, geçmiş, mesaj ve randevu okur")
    Rel(personal_agent, llm_runtime, "Kişisel özet ve konuşma özeti üretir")
```

## 4. C4 Component Diagram - Flutter

```mermaid
C4Component
    title Flutter Component Diyagramı - UI, State ve API

    Person(patient, "Hasta / Kullanıcı", "Mobil uygulama ile etkileşir.")
    System_Ext(api, "AI Agent API", "FastAPI backend")

    Container_Boundary(flutter, "Flutter Mobile App / frontend/lib") {
        Component(onboarding, "OnboardingScreen", "Flutter screen", "Oturum açma/kayıt ve başlangıç yönlendirmesi.")
        Component(chat_screen, "ChatScreen", "Flutter screen", "Mesajlaşma, kaynak gösterimi, handled_by etiketi, randevu/geçmiş aksiyon butonları.")
        Component(appointments_screen, "AppointmentsScreen", "Flutter screen", "Aktif randevular, iptal kayıtları ve önerilen slotları gösterir.")
        Component(history_screen, "HistoryScreen", "Flutter screen", "Personal Agent payloadını profil, kayıt, sohbet hafızası ve randevu bölümleriyle render eder.")
        Component(result_screen, "ResultScreen", "Flutter screen", "Oluşturulan randevu sonucunu gösterir.")

        Component(chat_bloc, "ChatBloc", "ChangeNotifier state", "Session, conversation_id, messages, suggestedSlots, appointments ve history payload state'i.")
        Component(repository, "ChatRepositoryImpl", "Repository adapter", "SharedPreferences session saklama ve FastApiClient çağrılarını domain entity'lerine mapleme.")
        Component(fastapi_client, "FastApiClient", "HTTP client", "login/register/me/chat/appointments/book/cancel endpointlerini çağırır.")
        Component(models, "MessageModel + Entities", "Dart models", "ChatResponse, source docs, appointment booking ve slot verisini UI modeline taşır.")
    }

    Rel(patient, onboarding, "Giriş/kayıt yapar")
    Rel(patient, chat_screen, "Mesaj gönderir")
    Rel(patient, appointments_screen, "Randevu görür/alır/iptal eder")
    Rel(patient, history_screen, "Geçmiş özetini inceler")

    Rel(onboarding, chat_bloc, "login/register/restore")
    Rel(chat_screen, chat_bloc, "sendMessage ve uiAction tüketimi")
    Rel(appointments_screen, chat_bloc, "refreshAppointments, bookSuggestedSlot, cancelBooking")
    Rel(history_screen, chat_bloc, "latestHistoryPayload görüntüler")
    Rel(chat_bloc, repository, "Domain repository çağırır")
    Rel(repository, fastapi_client, "HTTP işlemleri")
    Rel(repository, models, "API JSON -> entity mapleme")
    Rel(fastapi_client, api, "HTTP/JSON", "Bearer token")
```

## 5. Dynamic Diagram - Chat Mesajı ve Agent Routing

```mermaid
sequenceDiagram
    autonumber
    actor Kullanici as Hasta / Kullanıcı
    participant Flutter as Flutter ChatScreen + ChatBloc
    participant API as ChatController POST /api/v1/chat
    participant Auth as get_current_user + AuthService
    participant UseCase as ProcessMedicalQueryUseCase
    participant HistoryRepo as PostgresUserHistoryRepository
    participant Orchestrator as AgentOrchestrator
    participant Intent as IntentClassifier
    participant Info as Bilgi Ajanı
    participant Appointment as Randevu Ajanı
    participant Personal as Kişisel Geçmiş Ajanı
    participant DB as PostgreSQL
    participant RAG as RAGService + Vector DB
    participant LLM as Llama3QLoRAClient

    Kullanici->>Flutter: Mesaj yazar
    Flutter->>API: POST /chat {message, conversation_id}
    API->>Auth: Bearer token doğrula
    Auth->>DB: user_sessions + users oku
    Auth-->>API: current_user
    API->>UseCase: execute(user_id, message, conversation_id)
    UseCase->>HistoryRepo: ensure_conversation()
    HistoryRepo->>DB: conversations oku/yaz
    UseCase->>Orchestrator: process_query(HealthQuery)
    Orchestrator->>Intent: classify(query)
    Intent->>DB: Gerekirse son mesajları oku
    Intent->>LLM: Belirsiz durumda intent JSON iste
    LLM-->>Intent: {intent, reason, confidence}

    alt information
        Orchestrator->>Info: answer_medical_query()
        Info->>RAG: retrieve(query, k=3)
        RAG->>RAG: FAISS IndexFlatIP ile top-k ara; gerekirse fallback skorla
        Info->>LLM: Kaynak ve semptom ipucuyla cevap üret
        LLM-->>Info: Türkçe bilgi cevabı
        Info-->>Orchestrator: message + sources + payload
    else appointment
        Orchestrator->>Appointment: handle_appointment_request()
        Appointment->>DB: Profil ve son konuşma bağlamı oku
        Appointment->>LLM: Randevu parametrelerini JSON çıkar
        Appointment-->>Orchestrator: slot/booking payloadı
    else personal_history
        Orchestrator->>Personal: handle_history_query()
        Personal->>DB: Profil, history_entries, messages, appointments oku
        Personal->>LLM: Yakın konuşma ve kayıt özeti üret
        Personal-->>Orchestrator: history summary payloadı
    end

    Orchestrator-->>UseCase: Standart ChatResponse alanları
    UseCase->>HistoryRepo: save_interaction(user + assistant)
    HistoryRepo->>DB: messages + interaction history yaz
    API-->>Flutter: ChatResponse
    Flutter->>Flutter: ui_action'a göre kaynak/randevu/geçmiş göster
```

## 6. Dynamic Diagram - Randevu Arama, Alma ve İptal

```mermaid
sequenceDiagram
    autonumber
    actor Kullanici as Hasta / Kullanıcı
    participant Flutter as Flutter Appointments/Chat UI
    participant ChatAPI as ChatController
    participant ApptAPI as AppointmentController
    participant Agent as Randevu Ajanı
    participant Service as AppointmentService
    participant Hospital as HospitalMockAPI
    participant Repo as PostgresAppointmentRepository
    participant DB as PostgreSQL
    participant LLM as Llama3QLoRAClient

    Kullanici->>Flutter: "Yarın saat 10 KBB randevusu ara"
    Flutter->>ChatAPI: POST /chat
    ChatAPI->>Agent: appointment intent route
    Agent->>LLM: action, specialty, city, date, hour, slot seçimi JSON çıkar
    Agent->>Service: search_slots_with_fallbacks(preferences)
    Service->>Hospital: search_slots()
    Hospital-->>Service: Müsait slot listesi
    Service->>Repo: list_reserved_slot_ids()
    Repo->>DB: confirmed appointments oku
    Service-->>Agent: exact veya fallback slotlar
    Agent-->>Flutter: ui_action=show_appointment_options, slot_options

    Kullanici->>Flutter: "İlkini al" veya slot kartından "Bu Randevuyu Al"
    alt Chat içinden doğal dil booking
        Flutter->>ChatAPI: POST /chat "ilkini al"
        ChatAPI->>Agent: Yakın konuşmadaki slot bağlamıyla booking
        Agent->>Service: book_slot(slot_id)
    else Randevu ekranından direkt booking
        Flutter->>ApptAPI: POST /appointments/{slot_id}/book
        ApptAPI->>Service: book_slot(slot_id)
    end

    Service->>Repo: list_reserved_slot_ids()
    Service->>Hospital: book_slot(patient_id, slot_id)
    Hospital-->>Service: AppointmentBooking confirmed
    Service->>Repo: save_booking()
    Repo->>DB: appointments yaz
    Service-->>Flutter: Booking payload

    Kullanici->>Flutter: Randevuyu iptal et
    Flutter->>ApptAPI: POST /appointments/{booking_id}/cancel
    ApptAPI->>Service: cancel_booking(patient_id, booking_id)
    Service->>Hospital: cancel_booking(booking_id)
    Service->>Repo: cancel_booking()
    Repo->>DB: status=cancelled
    Service-->>Flutter: Cancelled booking payload
```

## 7. Data / ER Diagram

```mermaid
erDiagram
    users ||--o| patient_profiles : has
    users ||--o{ user_sessions : opens
    users ||--o{ patient_history_entries : owns
    users ||--o{ conversations : starts
    users ||--o{ appointments : books
    conversations ||--o{ messages : contains

    users {
        string id PK
        string username UK
        string password_hash
        string full_name
        datetime created_at
    }

    patient_profiles {
        string user_id PK, FK
        int age
        json chronic_conditions
        json medications
        text notes
        string city
        datetime updated_at
    }

    patient_history_entries {
        string id PK
        string user_id FK
        string entry_type
        text summary
        json metadata_json
        datetime recorded_at
    }

    conversations {
        string id PK
        string user_id FK
        string title
        datetime created_at
    }

    messages {
        string id PK
        string conversation_id FK
        string role
        text content
        datetime created_at
    }

    appointments {
        string id PK
        string user_id FK
        string external_booking_id UK
        string slot_id
        string hospital_name
        string city
        string physician_name
        string specialty
        datetime start_at
        string status
        datetime created_at
    }

    user_sessions {
        string id PK
        string user_id FK
        string token_hash UK
        datetime created_at
        datetime expires_at
        datetime revoked_at
    }
```

## 8. Deployment Diagram

```mermaid
C4Deployment
    title Deployment Diyagramı - Demo ve Sunum Ortamı

    Deployment_Node(mobile_device, "Kullanıcı Cihazı / Simulator", "iOS, Android veya Flutter simulator") {
        Container(flutter_app, "Flutter Mobile App", "Dart", "API_BASE_URL ile FastAPI backend'e bağlanır.")
    }

    Deployment_Node(dev_machine, "Demo Makinesi", "macOS / Linux") {
        Container(fastapi_app, "FastAPI Backend", "Python + Uvicorn", "backend/src/main.py")

        Deployment_Node(docker, "Docker Compose", "Docker Desktop") {
            ContainerDb(postgres, "PostgreSQL", "postgres:16", "medical_chatbot veritabanı")
        }

        Deployment_Node(local_files, "Local Model ve RAG Dosyaları", "Filesystem") {
            ContainerDb(chroma, "Chroma Fallback Cache", "SQLite-backed fallback store", "backend/data/rag/chroma")
            ContainerDb(rag_outputs, "Rapor RAG Outputs", "FAISS IndexFlatIP + chunks.parquet", "outputs altındaki rapor RAG artefactleri")
            Container(model_assets, "Model Assets", "HF model / PEFT adapter", "Meta-Llama-3-8B-Instruct, qlora adapter, merged model")
        }

        Container(ollama, "Ollama veya HF Local Runtime", "LLM inference", "Llama 3 / fine-tuned QLoRA model yanıt üretir.")
    }

    System_Ext(lab_pc, "Opsiyonel Okul Lab PC", "GPU inference server", "Aynı LLMEngine portuna uyacak şekilde HTTP LLM provider olarak bağlanabilir.")

    Rel(flutter_app, fastapi_app, "HTTP/JSON", "127.0.0.1 veya LAN URL")
    Rel(fastapi_app, postgres, "SQL", "DATABASE_URL")
    Rel(fastapi_app, rag_outputs, "Primary FAISS retrieval", "EXTERNAL_RAG_*")
    Rel(fastapi_app, chroma, "Fallback/cache retrieval", "CHROMA_PATH")
    Rel(fastapi_app, ollama, "Prompt", "LLM_BASE_URL")
    Rel(model_assets, ollama, "Model ağırlığı sağlar")
    Rel(fastapi_app, lab_pc, "Alternatif uzak LLM çağrısı", "HTTP, aynı LLMEngine adapter mantığı")
```

## 9. Koddan Çıkan Mimari Notlar

- `frontend/lib/data/datasources/remote/fastapi_client.dart` HTTP sınırıdır; `/auth`, `/chat` ve `/appointments` endpointlerini tüketir.
- `frontend/lib/presentation/blocs/chat_bloc.dart` mobil state merkezidir; `conversationId`, `suggestedSlots`, `appointments` ve `latestHistoryPayload` burada tutulur.
- `backend/src/presentation/dependencies.py` backend dependency graph merkezidir; agent, service, repository ve LLM adapter burada bağlanır.
- `backend/src/application/use_cases/process_medical_query.py` conversation oluşturma, orchestrator çağırma ve mesajları DB'ye kaydetme akışının ana use-case'idir.
- `backend/src/application/orchestrator/agent_orchestrator.py` tek agent routing noktasıdır.
- `backend/src/application/services/intent_classifier.py` önce rule-based karar verir, belirsiz durumda LLM'den yapılandırılmış intent JSON'u ister.
- `backend/src/application/agents/information_agent.py` RAG + LLM + semptom rehberiyle Bilgi Ajanı davranışını üretir.
- `backend/src/application/agents/appointment_agent.py` randevu parametre çıkarımı, slot listeleme, booking, cancel ve list akışını yönetir.
- `backend/src/application/agents/personal_agent.py` profil, geçmiş kayıt, randevu ve son mesajları kullanarak kişisel özet üretir.
- `backend/src/infrastructure/database/postgres/models.py` operasyonel veritabanı şemasının kaynağıdır.
- `backend/src/infrastructure/database/vector/faiss_chroma_db.py` rapordaki RAG artefactleri, Chroma store ve fallback retrieval davranışının adapterıdır.
- `backend/src/infrastructure/ai/llama3_qlora_client.py` plain Ollama, HF local ve HF adapter modlarını aynı `LLMEngine` portu arkasında toplar.
