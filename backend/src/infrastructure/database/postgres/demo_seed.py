from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from infrastructure.database.postgres.auth_db import hash_demo_password
from infrastructure.database.postgres.base import session_scope
from infrastructure.database.postgres.models import (
    AppointmentModel,
    ConversationModel,
    MessageModel,
    PatientHistoryEntryModel,
    PatientProfileModel,
    UserModel,
)


def ensure_demo_data() -> None:
    demo_users = [
        ("user_001", "senol@example.com", "Senol Erdem"),
        ("user_002", "ayse@example.com", "Ayse Demir"),
        ("user_003", "mehmet@example.com", "Mehmet Kaya"),
    ]
    legacy_usernames = {
        "user_001": "senol_demo",
        "user_002": "ayse_demo",
        "user_003": "mehmet_demo",
    }

    with session_scope() as session:
        existing_users = {
            user.id: user
            for user in session.query(UserModel).all()
        }

        if existing_users:
            changed = False
            for user_id, email, full_name in demo_users:
                existing = existing_users.get(user_id)
                if existing is not None:
                    if existing.username in {legacy_usernames[user_id], email}:
                        if existing.username != email:
                            existing.username = email
                            changed = True
                        if existing.full_name != full_name:
                            existing.full_name = full_name
                            changed = True
                        if existing.password_hash != hash_demo_password("1234"):
                            existing.password_hash = hash_demo_password("1234")
                            changed = True
                        continue

                by_email = session.query(UserModel).filter(UserModel.username == email).first()
                if by_email is None:
                    session.add(
                        UserModel(
                            id=user_id,
                            username=email,
                            password_hash=hash_demo_password("1234"),
                            full_name=full_name,
                        )
                    )
                    changed = True
            if changed:
                session.flush()
        else:
            users = [
                UserModel(
                    id=user_id,
                    username=email,
                    password_hash=hash_demo_password("1234"),
                    full_name=full_name,
                )
                for user_id, email, full_name in demo_users
            ]
            session.add_all(users)

        existing_profiles = {
            profile.user_id: profile
            for profile in session.query(PatientProfileModel).all()
        }
        if "user_001" not in existing_profiles:
            session.add(
                PatientProfileModel(
                    user_id="user_001",
                    age=24,
                    chronic_conditions=["alerjik rinit"],
                    medications=["antihistaminik"],
                    notes="KBB takibi var.",
                    city="Eskisehir",
                )
            )
        if "user_002" not in existing_profiles:
            session.add(
                PatientProfileModel(
                    user_id="user_002",
                    age=41,
                    chronic_conditions=["tip 2 diyabet"],
                    medications=["metformin"],
                    notes="Duzenli dahiliye kontrolu gerekiyor.",
                    city="Ankara",
                )
            )
        if "user_003" not in existing_profiles:
            session.add(
                PatientProfileModel(
                    user_id="user_003",
                    age=52,
                    chronic_conditions=["hipertansiyon"],
                    medications=["beta bloker"],
                    notes="Kardiyoloji kontrolleri duzenli.",
                    city="Istanbul",
                )
            )

        now = datetime.now(timezone.utc)
        existing_history = {
            (entry.user_id, entry.entry_type, entry.summary)
            for entry in session.query(PatientHistoryEntryModel).all()
        }
        history_seed = [
            ("user_001", "visit", "Gecen ay KBB polikliniginde alerji kontrolu yapildi."),
            ("user_001", "lab", "Temel kan degerleri referans araliginda."),
            ("user_002", "lab", "HbA1c degeri kontrol altinda ancak izlem devam etmeli."),
            ("user_002", "medication", "Metformin kullanimina devam ediyor."),
            ("user_003", "appointment", "Kardiyoloji kontrolleri icin aktif takip var."),
        ]
        for user_id, entry_type, summary in history_seed:
            if (user_id, entry_type, summary) not in existing_history:
                session.add(
                    PatientHistoryEntryModel(
                        user_id=user_id,
                        entry_type=entry_type,
                        summary=summary,
                        metadata_json={},
                    )
                )

        existing_demo_conversation = session.query(ConversationModel).filter(
            ConversationModel.user_id == "user_001",
            ConversationModel.title == "Baslangic gorusmesi",
        ).first()
        if existing_demo_conversation is None:
            conversation_id = str(uuid4())
            session.add(
                ConversationModel(
                    id=conversation_id,
                    user_id="user_001",
                    title="Baslangic gorusmesi",
                )
            )
            session.add_all(
                [
                    MessageModel(
                        conversation_id=conversation_id,
                        role="user",
                        content="Geçmiş kayıtlarımı özetler misin?",
                    ),
                    MessageModel(
                        conversation_id=conversation_id,
                        role="assistant",
                        content="Alerjik rinit ve KBB takibi odakli bir profiliniz var.",
                    ),
                ]
            )

        existing_seed_bookings = {
            booking.external_booking_id
            for booking in session.query(AppointmentModel).all()
        }
        appointment_seed = [
            ("user_003", "seed-booking-001", "slot-seed-001", "Acibadem", "Istanbul", "Dr. Selin Tas", "Kardiyoloji", now + timedelta(days=4), "confirmed"),
            ("user_001", "seed-booking-002", "slot-seed-002", "Eskisehir Sehir Hastanesi", "Eskisehir", "Dr. Burcu Inal", "Kulak Burun Bogaz", now + timedelta(days=2), "confirmed"),
            ("user_002", "seed-booking-003", "slot-seed-003", "Gazi Universite Hastanesi", "Ankara", "Dr. Murat Coskun", "Dahiliye", now + timedelta(days=3), "confirmed"),
            ("user_003", "seed-booking-004", "slot-seed-004", "Ankara Sehir Hastanesi", "Ankara", "Dr. Dilara Kurt", "Kardiyoloji", now + timedelta(days=6), "cancelled"),
        ]
        for user_id, external_booking_id, slot_id, hospital_name, city, physician_name, specialty, start_at, status in appointment_seed:
            if external_booking_id in existing_seed_bookings:
                continue
            session.add(
                AppointmentModel(
                    id=str(uuid4()),
                    user_id=user_id,
                    external_booking_id=external_booking_id,
                    slot_id=slot_id,
                    hospital_name=hospital_name,
                    city=city,
                    physician_name=physician_name,
                    specialty=specialty,
                    start_at=start_at,
                    status=status,
                    created_at=now,
                )
            )
