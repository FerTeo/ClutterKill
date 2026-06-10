import re
import logging
from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal

from ai.agent_extractor import ExtractorAgent
from ai.agent_decider import DeciderAgent, ActionDecision
from ai.tools import (
    extract_text_from_pdf,
    extract_text_from_image,
    extract_text_from_docx,
)
from ai.vision_tools import describe_image
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
        self.is_running = True

    @staticmethod
    def _build_descriptive_name(raw_text: str, original_filename: str) -> str:
        """Construiește un nume descriptiv din textul brut (conține Vision Analysis).

        Extrage cuvintele cheie din descrierea vizuală a imaginii
        și le combină într-un nume de fișier curat.
        Dacă nu găsește o descriere utilă, păstrează numele original.
        """
        ext = Path(original_filename).suffix  # .jpeg, .png, etc.

        # Extragem descrierea vizuală dacă există
        # Căutăm textul între "Image Vision Analysis:" și "Extracted OCR Text:"
        if "Image Vision Analysis:" not in raw_text:
            return original_filename

        # Extragem doar partea de Vision Analysis
        parts = raw_text.split("Image Vision Analysis:")
        if len(parts) < 2:
            return original_filename

        vision_part = parts[1]
        # Tăiem tot ce e după "Extracted OCR Text:" dacă există
        if "Extracted OCR Text:" in vision_part:
            vision_part = vision_part.split("Extracted OCR Text:")[0]

        desc = vision_part.strip()

        # Dacă descrierea e goală sau e o eroare, păstrăm numele original
        if not desc or desc.startswith("Eroare"):
            return original_filename

        # Sanitizare rapidă pentru a fi un nume de fișier valid (păstrăm litere, cifre, underscore, cratimă)
        cleaned_desc = re.sub(r"[^a-zA-Z0-9_\-]", "", desc.replace(" ", "_"))
        
        if not cleaned_desc:
            return original_filename
            
        # Asigură-te că nu se dublează extensia
        if cleaned_desc.lower().endswith(ext.lower()):
            return cleaned_desc
            
        return cleaned_desc + ext

    def run(self):
        # 1. Inițializăm agenții
        self.log_updated.emit("Se încarcă agenții AI...")
        try:
            extractor = ExtractorAgent()
            decider = DeciderAgent()
        except Exception as e:
            self.log_updated.emit(f"Eroare la inițializarea agenților: {e}")
            self.scan_finished.emit(0)
            return

        # 2. Încărcăm Șablonul (Template-ul) din DB
        if not hasattr(self, 'user_rule') or not self.user_rule.strip():
            self.log_updated.emit("Niciun preset nu a fost selectat!")
            self.scan_finished.emit(0)
            return
            
        import core.rules_db as rules_db
        from ai.agent_compiler import CompiledRule
        
        rule_record = rules_db.get_rule_by_name(self.user_rule)
        if not rule_record:
            self.log_updated.emit(f"Eroare: Presetul '{self.user_rule}' nu a fost găsit în baza de date.")
            return

        # Creăm un mock CompiledRule pentru a-l pasa mai departe Decider-ului
        compiled_rule = CompiledRule(
            category=rule_record['query'],
            folder_structure=rule_record['folder_template'],
            naming_convention=rule_record['naming_template']
        )
        
        self.log_updated.emit(f"Preset încărcat: {compiled_rule.folder_structure} | {compiled_rule.naming_convention}")

        # 3. Preluăm fișierele din sursă (ignorând fișierele ascunse macOS gen .DS_Store)
        files = [f for f in self.source_dir.rglob("*") if f.is_file() and not f.name.startswith(".")]
        total = len(files)

        if total == 0:
            self.log_updated.emit("Niciun fișier găsit în folderul sursă.")
            self.scan_finished.emit(0)
            return

        self.log_updated.emit(f"{total} fișiere găsite. Se începe scanarea cu AI...")

        added_count = 0
        skipped_count = 0

        existing_paths = {r["original_path"] for r in quarantine_db.get_all()}

        for i, file_path in enumerate(files):
            str_path = str(file_path)

            if str_path in existing_paths:
                skipped_count += 1
                self.log_updated.emit(f"{file_path.name} — deja în carantină, skip")
            else:
                self.log_updated.emit(f"Procesare: {file_path.name}...")

                # a. Extragere text
                text = ""
                ext = file_path.suffix.lower()
                try:
                    if ext == ".pdf":
                        text = extract_text_from_pdf(file_path)
                    elif ext in [".png", ".jpg", ".jpeg", ".bmp", ".tiff"]:
                        ocr_text = extract_text_from_image(file_path)
                        self.log_updated.emit("  Vision: Se analizează conținutul vizual...")
                        vision_desc = describe_image(file_path)
                        text = f"Image Vision Analysis:\n{vision_desc}\n\nExtracted OCR Text:\n{ocr_text}"
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
                # ── BYPASS: Dacă categoria e "any"/"all", NU mai întrebăm AI-ul ──
                # Modelul de 2B e prea mic și trimite în carantină aleatoriu.
                # Construim decizia deterministic în cod.
                try:
                    cat = compiled_rule.category.strip().lower()
                    if cat in ("any", "all"):
                        # Construim numele descriptiv direct din summary
                        naming = compiled_rule.naming_convention.strip()
                        if naming == "descriptive_name_based_on_content" or naming == "":
                            if "Image Vision Analysis:" in text:
                                suggested = self._build_descriptive_name(text, file_path.name)
                            else:
                                if hasattr(extraction_result, "suggested_filename") and extraction_result.suggested_filename:
                                    suggested = extraction_result.suggested_filename
                                    if not suggested.lower().endswith(file_path.suffix.lower()):
                                        suggested += file_path.suffix
                                else:
                                    suggested = file_path.name
                        elif naming == "{original_filename}":
                            suggested = file_path.name
                        else:
                            suggested = file_path.name

                        target_folder = compiled_rule.folder_structure
                        if target_folder.strip().lower() in ("any", "all", ""):
                            target_folder = "Organized"

                        decision = ActionDecision(
                            status="move",
                            suggested_name=suggested,
                            suggested_folder=target_folder,
                        )
                        logger.info(
                            "BYPASS (category=any): forțăm MOVE pentru %s -> %s",
                            file_path.name, suggested,
                        )
                    else:
                        decision = decider.decide(summary, file_path.name, compiled_rule)

                    if decision.status == "move":
                        proposed_folder = str(self.dest_dir / decision.suggested_folder)

                        # Mutăm și redenumim fișierul fizic imediat
                        try:
                            final_path = move_and_rename_file(
                                str_path, proposed_folder, decision.suggested_name
                            )
                            added_count += 1
                            self.log_updated.emit(
                                f"  MOVE: Mutat și redenumit cu succes în -> {final_path}"
                            )
                        except Exception as e:
                            logger.error(
                                f"Eroare la mutarea fișierului {file_path.name}: {e}"
                            )
                            self.log_updated.emit(f"  Eroare la mutare: {e}")

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
                            f"  QUARANTINE: Trimis în carantină. Nume sugerat: {decision.suggested_name}"
                        )
                except Exception as e:
                    logger.error(f"Eroare DeciderAgent: {e}")
                    self.log_updated.emit(f"  Eroare la luarea deciziei: {e}")

            # Actualizăm progresul
            progress = int((i + 1) / total * 100)
            self.progress_updated.emit(progress)

        self.log_updated.emit(
            f"\nScanare AI completă! {added_count} fișiere noi trimise spre review, "
            f"{skipped_count} existente ignorate."
        )
        self.scan_finished.emit(added_count)
