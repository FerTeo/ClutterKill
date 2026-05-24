import logging
from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal

from ai.agent_compiler import CompilerAgent
from ai.agent_extractor import ExtractorAgent
from ai.agent_decider import DeciderAgent
from ai.tools import (
    extract_text_from_pdf,
    extract_text_from_image,
    extract_text_from_docx,
)
from core.file_manager import move_and_rename_file
from core.quarantine_db import quarantine_db

logger = logging.getLogger(__name__)


class ScanWorker(QThread):
    """
    Thread real de scanare care folosește pipeline-ul de agenți AI:
    1. Agent 0 (Compiler) transformă regula naturală.
    2. Agent 1 (Extractor) citește fișierul și scoate un rezumat tehnic.
    3. Agent 2 (Decider) aplică regula pe rezumat pentru o decizie de rutare.
    4. Adaugă fiecare fișier în quarantine_db cu recomandările AI.
    """

    progress_updated = pyqtSignal(int)
    log_updated = pyqtSignal(str)
    scan_finished = pyqtSignal(int)

    def __init__(self, source_dir: str, dest_dir: str, user_rule: str):
        super().__init__()
        self.source_dir = Path(source_dir)
        self.dest_dir = Path(dest_dir)
        self.user_rule = user_rule

    def run(self):
        # 1. Inițializăm agenții
        self.log_updated.emit("🤖 Se încarcă agenții AI...")
        try:
            compiler = CompilerAgent()
            extractor = ExtractorAgent()
            decider = DeciderAgent()
        except Exception as e:
            self.log_updated.emit(f"❌ Eroare la inițializarea agenților: {e}")
            self.scan_finished.emit(0)
            return

        # 2. Compilăm regula
        if not self.user_rule.strip():
            self.log_updated.emit("⚠️ Regula nu a fost completată!")
            self.scan_finished.emit(0)
            return

        self.log_updated.emit(f"🧠 Compilare regulă: '{self.user_rule}'")
        try:
            compiled_rule = compiler.compile(self.user_rule)
            self.log_updated.emit(
                f"✅ Regulă compilată:\n{compiled_rule.model_dump_json(indent=2)}"
            )
        except Exception as e:
            self.log_updated.emit(f"❌ Eroare la compilarea regulii: {e}")
            self.scan_finished.emit(0)
            return

        # 3. Preluăm fișierele din sursă
        files = [f for f in self.source_dir.rglob("*") if f.is_file()]
        total = len(files)

        if total == 0:
            self.log_updated.emit("⚠️ Niciun fișier găsit în folderul sursă.")
            self.scan_finished.emit(0)
            return

        self.log_updated.emit(f"🔍 {total} fișiere găsite. Se începe scanarea cu AI...")

        added_count = 0
        skipped_count = 0

        existing_paths = {r["original_path"] for r in quarantine_db.get_all()}

        for i, file_path in enumerate(files):
            str_path = str(file_path)

            if str_path in existing_paths:
                skipped_count += 1
                self.log_updated.emit(f"⏭️ {file_path.name} — deja în carantină, skip")
            else:
                self.log_updated.emit(f"📄 Procesare: {file_path.name}...")

                # a. Extragere text
                text = ""
                ext = file_path.suffix.lower()
                try:
                    if ext == ".pdf":
                        text = extract_text_from_pdf(file_path)
                    elif ext in [".png", ".jpg", ".jpeg", ".bmp", ".tiff"]:
                        text = extract_text_from_image(file_path)
                    elif ext == ".docx":
                        text = extract_text_from_docx(file_path)
                    elif ext in [".txt", ".csv", ".md"]:
                        text = file_path.read_text(errors="ignore")
                    else:
                        text = f"Fișier de tip necunoscut ({ext}). Conținut text nedisponibil."
                except Exception as e:
                    logger.warning(
                        f"Eroare extragere text pentru {file_path.name}: {e}"
                    )
                    text = f"Eroare extracție: {e}"

                # b. Agent 1 (Extragere)
                try:
                    extraction_result = extractor.extract(
                        text or "Conținut gol sau necitibil"
                    )
                    summary = extraction_result.get_technical_summary()
                except Exception as e:
                    logger.error(f"Eroare ExtractorAgent: {e}")
                    summary = f"Eroare procesare text: {e}"

                # c. Agent 2 (Decizie)
                try:
                    decision = decider.decide(summary, file_path.name, compiled_rule)

                    if decision.status == "move":
                        proposed_folder = str(self.dest_dir / decision.suggested_folder)

                        # Mutăm și redenumim fișierul fizic imediat
                        try:
                            move_and_rename_file(
                                str_path, proposed_folder, decision.suggested_name
                            )
                            added_count += 1
                            self.log_updated.emit(
                                f"  ↳ MOVE: Mutat și redenumit cu succes în -> {proposed_folder}/{decision.suggested_name}"
                            )
                        except Exception as e:
                            logger.error(
                                f"Eroare la mutarea fișierului {file_path.name}: {e}"
                            )
                            self.log_updated.emit(f"  ↳ ❌ Eroare la mutare: {e}")

                    else:
                        proposed_folder = "Quarantine"

                        # Adăugăm în carantină pentru intervenție manuală
                        quarantine_db.add(
                            original_path=str_path,
                            ai_proposed_name=decision.suggested_name,
                            ai_proposed_folder=proposed_folder,
                            reason=f"Decizie AI ({decision.status}) bazată pe: {summary[:100]}...",
                        )
                        added_count += 1
                        self.log_updated.emit(
                            f"  ↳ QUARANTINE: Trimis în carantină. Nume sugerat: {decision.suggested_name}"
                        )
                except Exception as e:
                    logger.error(f"Eroare DeciderAgent: {e}")
                    self.log_updated.emit(f"  ↳ ❌ Eroare la luarea deciziei: {e}")

            # Actualizăm progresul
            progress = int((i + 1) / total * 100)
            self.progress_updated.emit(progress)

        self.log_updated.emit(
            f"\n✅ Scanare AI completă! {added_count} fișiere noi trimise spre review, "
            f"{skipped_count} existente ignorate."
        )
        self.scan_finished.emit(added_count)
