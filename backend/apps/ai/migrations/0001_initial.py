"""Initial migration for the AI app."""

from __future__ import annotations

import uuid

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    """Create the initial AI support and operations schema."""

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="KnowledgeSource",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=200)),
                (
                    "source_type",
                    models.CharField(
                        choices=[
                            ("manual", "Manual"),
                            ("faq", "FAQ"),
                            ("cms", "CMS"),
                            ("doc", "Document"),
                            ("pdf", "PDF"),
                        ],
                        default="manual",
                        max_length=50,
                    ),
                ),
                ("uri", models.TextField(blank=True)),
                ("is_active", models.BooleanField(default=True)),
                ("sync_cursor", models.TextField(blank=True)),
                ("last_synced_at", models.DateTimeField(blank=True, null=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="WorkflowRun",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("workflow_type", models.CharField(max_length=50)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("running", "Running"),
                            ("completed", "Completed"),
                            ("cancelled", "Cancelled"),
                            ("failed", "Failed"),
                        ],
                        default="pending",
                        max_length=20,
                    ),
                ),
                ("actor_type", models.CharField(default="agent", max_length=20)),
                ("input_payload", models.JSONField(blank=True, default=dict)),
                ("result_payload", models.JSONField(blank=True, default=dict)),
                ("idempotency_key", models.CharField(max_length=100, unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="Conversation",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                (
                    "channel",
                    models.CharField(
                        choices=[
                            ("web", "Web"),
                            ("backoffice", "Backoffice"),
                            ("whatsapp", "WhatsApp"),
                            ("email", "Email"),
                        ],
                        default="web",
                        max_length=30,
                    ),
                ),
                ("mode", models.CharField(choices=[("support", "Support"), ("ops", "Operations")], default="support", max_length=20)),
                ("session_key", models.CharField(blank=True, max_length=100)),
                (
                    "status",
                    models.CharField(
                        choices=[("open", "Open"), ("escalated", "Escalated"), ("closed", "Closed")],
                        default="open",
                        max_length=20,
                    ),
                ),
                ("last_intent", models.CharField(blank=True, max_length=50)),
                ("summary", models.TextField(blank=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "customer",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=models.deletion.SET_NULL,
                        related_name="ai_conversations",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"ordering": ["-updated_at"]},
        ),
        migrations.CreateModel(
            name="KnowledgeDocument",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("external_id", models.CharField(max_length=200)),
                ("title", models.CharField(max_length=300)),
                ("language", models.CharField(default="es-AR", max_length=10)),
                (
                    "channel",
                    models.CharField(choices=[("public", "Public"), ("internal", "Internal")], default="public", max_length=30),
                ),
                ("checksum", models.CharField(max_length=64)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("is_active", models.BooleanField(default=True)),
                ("published_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "source",
                    models.ForeignKey(on_delete=models.deletion.PROTECT, related_name="documents", to="ai.knowledgesource"),
                ),
            ],
            options={"ordering": ["title"]},
        ),
        migrations.CreateModel(
            name="ConversationTurn",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("role", models.CharField(choices=[("user", "User"), ("assistant", "Assistant"), ("tool", "Tool"), ("system", "System")], max_length=20)),
                ("content", models.TextField()),
                ("citations", models.JSONField(blank=True, default=list)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "conversation",
                    models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="turns", to="ai.conversation"),
                ),
            ],
            options={"ordering": ["created_at"]},
        ),
        migrations.CreateModel(
            name="MemoryFact",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("fact_type", models.CharField(max_length=50)),
                ("key", models.CharField(max_length=100)),
                ("value", models.JSONField(blank=True, default=dict)),
                ("confidence", models.DecimalField(decimal_places=3, default=0.8, max_digits=4)),
                ("expires_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "conversation",
                    models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="facts", to="ai.conversation"),
                ),
            ],
            options={"ordering": ["-updated_at"]},
        ),
        migrations.CreateModel(
            name="KnowledgeChunk",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("chunk_index", models.PositiveIntegerField()),
                ("section", models.CharField(blank=True, max_length=200)),
                ("content", models.TextField()),
                ("embedding", models.JSONField(blank=True, default=list)),
                ("token_count", models.PositiveIntegerField(default=0)),
                ("embedding_model", models.CharField(blank=True, max_length=100)),
                ("content_hash", models.CharField(max_length=64)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "document",
                    models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="chunks", to="ai.knowledgedocument"),
                ),
            ],
            options={"ordering": ["document", "chunk_index"]},
        ),
        migrations.CreateModel(
            name="ConversationFeedback",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("value", models.CharField(choices=[("positive", "Positive"), ("negative", "Negative")], max_length=20)),
                ("note", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "conversation",
                    models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="feedback_items", to="ai.conversation"),
                ),
                (
                    "turn",
                    models.ForeignKey(blank=True, null=True, on_delete=models.deletion.SET_NULL, related_name="feedback_items", to="ai.conversationturn"),
                ),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="AgentRun",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("agent_type", models.CharField(choices=[("support", "Support"), ("ops", "Operations"), ("workflow", "Workflow")], max_length=30)),
                ("model", models.CharField(blank=True, max_length=100)),
                ("status", models.CharField(choices=[("running", "Running"), ("completed", "Completed"), ("failed", "Failed")], default="running", max_length=20)),
                ("intent", models.CharField(blank=True, max_length=50)),
                ("message_text", models.TextField(blank=True)),
                ("response_text", models.TextField(blank=True)),
                ("citations", models.JSONField(blank=True, default=list)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("confidence", models.DecimalField(blank=True, decimal_places=3, max_digits=4, null=True)),
                ("needs_human", models.BooleanField(default=False)),
                ("prompt_version", models.CharField(default="v1", max_length=50)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "conversation",
                    models.ForeignKey(blank=True, null=True, on_delete=models.deletion.SET_NULL, related_name="runs", to="ai.conversation"),
                ),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="ApprovalRequest",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("action_name", models.CharField(max_length=100)),
                ("action_payload", models.JSONField(blank=True, default=dict)),
                ("status", models.CharField(choices=[("pending", "Pending"), ("approved", "Approved"), ("rejected", "Rejected")], default="pending", max_length=20)),
                ("decision_note", models.TextField(blank=True)),
                ("decided_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "approved_by",
                    models.ForeignKey(blank=True, null=True, on_delete=models.deletion.SET_NULL, related_name="ai_approvals", to=settings.AUTH_USER_MODEL),
                ),
                (
                    "workflow_run",
                    models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="approvals", to="ai.workflowrun"),
                ),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="ToolExecution",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("tool_name", models.CharField(max_length=100)),
                (
                    "risk_level",
                    models.CharField(
                        choices=[
                            ("read_only", "Read only"),
                            ("low_risk_write", "Low risk write"),
                            ("high_risk_write", "High risk write"),
                        ],
                        default="read_only",
                        max_length=20,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("succeeded", "Succeeded"),
                            ("failed", "Failed"),
                            ("blocked", "Blocked"),
                        ],
                        default="pending",
                        max_length=20,
                    ),
                ),
                ("input_payload", models.JSONField(blank=True, default=dict)),
                ("output_payload", models.JSONField(blank=True, default=dict)),
                ("latency_ms", models.PositiveIntegerField(default=0)),
                ("error", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "run",
                    models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="tool_executions", to="ai.agentrun"),
                ),
            ],
            options={"ordering": ["created_at"]},
        ),
        migrations.AddConstraint(
            model_name="knowledgedocument",
            constraint=models.UniqueConstraint(fields=("source", "external_id"), name="unique_knowledge_document_per_source"),
        ),
        migrations.AddConstraint(
            model_name="memoryfact",
            constraint=models.UniqueConstraint(fields=("conversation", "fact_type", "key"), name="unique_memory_fact_per_conversation"),
        ),
        migrations.AddConstraint(
            model_name="knowledgechunk",
            constraint=models.UniqueConstraint(fields=("document", "chunk_index"), name="unique_chunk_index_per_document"),
        ),
        migrations.AddIndex(
            model_name="knowledgechunk",
            index=models.Index(fields=["document", "chunk_index"], name="ai_knowledg_documen_6e6d84_idx"),
        ),
    ]
