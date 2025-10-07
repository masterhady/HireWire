from django.core.management.base import BaseCommand
from django.db import connection
from api.supabase_models import Job
from api.rag import embed_text, chunk_text
from decouple import config
import uuid

EMB_DIM = config("FIREWORKS_EMBEDDING_DIM", default=None, cast=int)


class Command(BaseCommand):
    help = "Re-index job embeddings into job_embeddings table."

    def add_arguments(self, parser):
        parser.add_argument(
            "--only-missing",
            action="store_true",
            help="Only generate embeddings for jobs that do not have embeddings yet",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=0,
            help="Limit number of jobs to process (0 = no limit)",
        )

    def handle(self, *args, **options):
        only_missing = options["only_missing"]
        limit = options["limit"]

        # determine job queryset
        qs = Job.objects.all()

        if only_missing:
            # find job ids that already have embeddings
            with connection.cursor() as c:
                c.execute("SELECT DISTINCT job_id FROM job_embeddings")
                rows = c.fetchall()
            existing_ids = {str(r[0]) for r in rows}
            qs = qs.exclude(id__in=existing_ids)

        if limit and limit > 0:
            qs = qs[:limit]

        total = qs.count()
        self.stdout.write(f"Processing {total} jobs (only_missing={only_missing}, limit={limit})")

        processed = 0
        inserted = 0
        errors = []

        for job in qs:
            processed += 1
            title = job.title
            description = getattr(job, "description", "") or ""
            requirements = getattr(job, "requirements", "") or ""
            text = f"{title}\n{description}\n{requirements}".strip()
            if not text:
                continue

            chunks = chunk_text(text)
            for i, chunk in enumerate(chunks or []):
                try:
                    emb = embed_text(chunk)
                    if EMB_DIM and len(emb) != EMB_DIM:
                        errors.append(f"job {job.id} chunk {i}: unexpected dim {len(emb)}")
                        continue

                    emb_literal = "[" + ",".join(map(str, emb)) + "]"
                    with connection.cursor() as c:
                        c.execute(
                            "INSERT INTO job_embeddings (id, job_id, created_at, embedding) VALUES (%s, %s, NOW(), %s::vector)",
                            [str(uuid.uuid4()), str(job.id), emb_literal],
                        )
                    inserted += 1
                except Exception as e:
                    errors.append(f"job {job.id} chunk {i}: {e}")

        self.stdout.write(f"Done. processed={processed}, inserted_chunks={inserted}, errors={len(errors)}")
        if errors:
            self.stdout.write("Errors (first 20):")
            for e in errors[:20]:
                self.stdout.write(str(e))
