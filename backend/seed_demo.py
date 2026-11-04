"""Create a fresh database and synthetic demo rows.

Run from the backend directory after exporting ADMIN_PASSWORD and
MEMBER_PASSWORD. Passwords are never written into the repository.
Demo accounts use example.com addresses only.
"""
import json
import os
import sys
from datetime import datetime, timedelta, date

_WEAK_PASSWORDS = {
    "",
    "admin123",
    "password",
    "test123",
    "changeme",
    "12345678",
    "123456789012",
}


def _require_password(name):
    value = os.environ.get(name, "")
    if len(value) < 12 or value.lower() in _WEAK_PASSWORDS:
        print(
            f"{name} must be an environment variable of at least 12 characters "
            "and must not be a well-known password.",
            file=sys.stderr,
        )
        sys.exit(1)
    return value


def main():
    admin_password = _require_password("ADMIN_PASSWORD")
    member_password = _require_password("MEMBER_PASSWORD")
    admin_email = os.environ.get("ADMIN_EMAIL", "admin@example.com")
    member_email = os.environ.get("MEMBER_EMAIL", "member@example.com")
    if not admin_email.endswith("@example.com") or not member_email.endswith("@example.com"):
        print("Demo emails must stay on example.com.", file=sys.stderr)
        sys.exit(1)

    from flask_migrate import upgrade

    from app import create_app
    from app.models import db
    from app.models.achievement import Achievement
    from app.models.meeting import Meeting, MeetingParticipant
    from app.models.project import Project, ProjectMember
    from app.models.tech_summary import TechSummary
    from app.models.user import Role, User

    app = create_app(os.getenv("FLASK_CONFIG") or "default")
    with app.app_context():
        upgrade()
        Role.insert_roles()

        admin = User.query.filter_by(email=admin_email).first()
        if admin is None:
            admin = User(
                email=admin_email,
                username="demo-admin",
                password=admin_password,
                name="示例管理员",
            )
            admin.role = Role.query.filter_by(name="Administrator").first()
            db.session.add(admin)

        member = User.query.filter_by(email=member_email).first()
        if member is None:
            member = User(
                email=member_email,
                username="demo-member",
                password=member_password,
                name="示例成员",
            )
            db.session.add(member)
        db.session.commit()

        if TechSummary.query.count() == 0:
            db.session.add(TechSummary(
                title="示例技术总结",
                content="这是一条不含个人信息的示例技术总结，用于演示语料重建。关键词：demo-corpus-anchor。",
                summary_type="示例",
                tags="demo",
                user_id=admin.id,
                source_url="https://example.com/demo-note",
                access_scope="lab",
            ))
            corpus_path = os.path.join(os.path.dirname(__file__), "evals", "corpus.jsonl")
            if os.path.exists(corpus_path):
                with open(corpus_path, encoding="utf-8") as handle:
                    for line in handle:
                        row = json.loads(line)
                        db.session.add(TechSummary(
                            title=row["title"],
                            content=row["content"],
                            summary_type="示例",
                            tags="eval",
                            user_id=admin.id,
                            source_url=row.get("source_url") or "https://example.com/seed",
                            access_scope=row.get("access_scope") or "lab",
                        ))
        if Achievement.query.count() == 0:
            db.session.add(Achievement(
                title="示例成果",
                description="合成的成果记录，不对应真实论文或人员。",
                achievement_type="示例",
                authors="示例成员",
                publish_date=date.today(),
                user_id=admin.id,
            ))
        if Project.query.count() == 0:
            project = Project(
                name="示例项目",
                description="合成的项目记录。",
                status="进行中",
                priority="中",
                creator_id=admin.id,
            )
            db.session.add(project)
            db.session.flush()
            db.session.add(ProjectMember(project_id=project.id, user_id=member.id, role="成员"))
        else:
            project = Project.query.first()
        if Meeting.query.count() == 0:
            start = datetime.utcnow() + timedelta(days=7)
            meeting = Meeting(
                title="示例会议",
                description="合成的会议记录。",
                location="示例会议室",
                status="计划中",
                start_time=start,
                end_time=start + timedelta(hours=1),
                organizer_id=admin.id,
                project_id=project.id if project else None,
            )
            db.session.add(meeting)
            db.session.flush()
            db.session.add(MeetingParticipant(meeting_id=meeting.id, user_id=member.id, role="参与者"))
        db.session.commit()
        from app.rag.ingest import rebuild_from_db
        from app.rag.service import sync_corpus_from_db

        sync_corpus_from_db()
        rebuild_from_db()
        print(
            "Demo database ready. "
            f"tech_summaries={TechSummary.query.count()} "
            f"users={User.query.count()}"
        )


if __name__ == "__main__":
    main()
