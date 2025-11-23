# server.py
import logging
import json
from tempfile import NamedTemporaryFile
from typing import Dict, Any
import io
import os
from datetime import datetime

from fastapi import FastAPI, Request, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
import uvicorn

from agent.research_agent import ResearchAgent
from agent.plan_editor import PlanEditor
from agent import voice as voice_mod

# reportlab
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader

logger = logging.getLogger("server")
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Company Research Assistant API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

research_agent = ResearchAgent()
editor = PlanEditor()

# optional logo path
LOGO_PATH = os.path.join(os.path.dirname(__file__), "static", "logo.png")


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception for request %s: %s", request.url, exc)
    return JSONResponse(status_code=500, content={"error": "internal_server_error", "detail": str(exc)})


@app.post("/api/research")
async def api_research(payload: Dict[str, Any]):
    try:
        query = payload.get("query") if isinstance(payload, dict) else None
        if not query:
            return JSONResponse(status_code=400, content={"error": "missing_query"})

        # --- Lightweight input validation (non-invasive) ---
        # Remove a leading 'research' keyword so users who type "Research X" still pass.
        cleaned = str(query).strip()
        if cleaned.lower().startswith("research"):
            candidate = cleaned[len("research"):].strip()
        else:
            candidate = cleaned

        # Count alphabetic characters in the candidate (basic heuristic).
        # If there are too few letters, treat it as invalid input (e.g., "1234!!!!").
        import re
        letters_count = len(re.findall(r"[A-Za-z]", candidate))
        if letters_count < 3:
            return JSONResponse(
                status_code=400,
                content={
                    "error": "invalid_input",
                    "detail": "Invalid input — please enter a valid company name or research query (e.g., 'Research Tesla' or 'Research EightFold AI')."
                }
            )
        # -------------------------------------------------------

        research_text, sources = research_agent.search_company(query)
        plan = research_agent.generate_account_plan(research_text, sources, query)
        return JSONResponse(status_code=200, content={"plan": plan})
    except Exception as e:
        logger.exception("api_research failed: %s", e)
        return JSONResponse(status_code=500, content={"error": "api_research_failed", "detail": str(e)})



@app.post("/api/edit")
async def api_edit(payload: Dict[str, Any]):
    try:
        plan = payload.get("plan")
        section = payload.get("section")
        content = payload.get("content")
        if not plan or not section:
            return JSONResponse(status_code=400, content={"error": "plan_and_section_required"})
        msg = editor.edit_section(plan, section, content)
        return JSONResponse(status_code=200, content={"ok": True, "message": msg, "plan": plan})
    except Exception as e:
        logger.exception("api_edit failed: %s", e)
        return JSONResponse(status_code=500, content={"error": "api_edit_failed", "detail": str(e)})


@app.post("/api/transcribe")
async def api_transcribe(file: UploadFile = File(...)):
    try:
        with NamedTemporaryFile(delete=False, suffix=".webm") as tf:
            data = await file.read()
            tf.write(data)
            tmp_path = tf.name

        text = voice_mod.transcribe_audio(tmp_path)
        return JSONResponse(status_code=200, content={"text": text or ""})
    except Exception as e:
        logger.exception("api_transcribe failed: %s", e)
        return JSONResponse(status_code=500, content={"error": "transcription_failed", "detail": str(e)})


@app.post("/api/export_pdf")
async def api_export_pdf(payload: Dict[str, Any]):
    """
    Generate a readable single-column PDF from plan JSON and return it.
    Payload: { plan: {...}, filename: optional_str }
    """
    try:
        plan = payload.get("plan")
        if not plan or not isinstance(plan, dict):
            return JSONResponse(status_code=400, content={"error": "plan_required"})

        buffer = io.BytesIO()
        pagesize = A4
        left_margin = right_margin = 20 * mm
        top_margin = bottom_margin = 20 * mm

        doc = SimpleDocTemplate(
            buffer,
            pagesize=pagesize,
            leftMargin=left_margin,
            rightMargin=right_margin,
            topMargin=top_margin,
            bottomMargin=bottom_margin,
            title="Account Plan",
            author="Company Research Agent"
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "Title",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=18,
            leading=22,
            spaceAfter=8
        )
        heading_style = ParagraphStyle(
            "Heading",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=14,
            spaceBefore=8,
            spaceAfter=6
        )
        body_style = ParagraphStyle(
            "Body",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=11,
            leading=15,
            spaceAfter=6
        )
        small_style = ParagraphStyle(
            "Small",
            parent=styles["BodyText"],
            fontName="Helvetica-Oblique",
            fontSize=9,
            leading=11,
            textColor=colors.HexColor("#555555"),
            spaceAfter=4
        )

        story = []

        # Header: optional logo + title + date
        # If logo exists, show on left; title on right.
        if os.path.exists(LOGO_PATH):
            try:
                logo = ImageReader(LOGO_PATH)
                im = Image(LOGO_PATH, width=50, height=50)
                # place logo + title using a small table
                header_tbl = [
                    [im, Paragraph(f"<b>Account Plan</b><br/><font size=10>{(plan.get('company_overview') or '')[:80]}</font>")]
                ]
                tbl = Table(header_tbl, colWidths=[50, doc.width - 50])
                tbl.setStyle(TableStyle([
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('LEFTPADDING', (0, 0), (-1, -1), 0),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                ]))
                story.append(tbl)
                story.append(Spacer(1, 10))
            except Exception:
                # fallback to plain title
                story.append(Paragraph("Account Plan", title_style))
        else:
            story.append(Paragraph("Account Plan", title_style))

        # metadata line
        gen_date = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
        story.append(Paragraph(f"Generated: {gen_date}", small_style))
        if plan.get("confidence_estimate"):
            story.append(Paragraph(f"Confidence estimate: {plan.get('confidence_estimate')}", small_style))
        story.append(Spacer(1, 8))

        # Helper to split text into paragraphs
        def add_long_text_as_paragraphs(title, text):
            story.append(Paragraph(title, heading_style))
            if not text or not str(text).strip():
                story.append(Paragraph("<i>Not available</i>", small_style))
                story.append(Spacer(1, 6))
                return
            # normalize and split on double newlines, keep lines wrapped
            txt = str(text).strip()
            # Replace Windows CRLF
            txt = txt.replace("\r\n", "\n")
            paras = [p.strip() for p in txt.split("\n\n") if p.strip()]
            for p in paras:
                # replace single newlines inside paragraph with <br/>
                safe = p.replace("\n", "<br/>")
                story.append(Paragraph(safe, body_style))
            story.append(Spacer(1, 6))

        # Add the core sections in intended order with good spacing
        add_long_text_as_paragraphs("Company Overview", plan.get("company_overview", ""))
        add_long_text_as_paragraphs("Key Findings", plan.get("key_findings", ""))
        add_long_text_as_paragraphs("Pain Points", plan.get("pain_points", ""))
        add_long_text_as_paragraphs("Opportunities", plan.get("opportunities", ""))
        add_long_text_as_paragraphs("Competitors", plan.get("competitors", ""))
        add_long_text_as_paragraphs("Recommended Strategy", plan.get("recommended_strategy", ""))

        # Sources - render as compact table (wrap URLs)
        sources = plan.get("sources", []) or []
        story.append(Spacer(1, 8))
        story.append(Paragraph("Sources", heading_style))
        if sources:
            # limit sources to reasonable number
            data = [["#", "Source"]]
            for i, s in enumerate(sources[:150], start=1):
                data.append([str(i), s])
            col_widths = [20, doc.width - 20]
            tbl = Table(data, colWidths=col_widths, hAlign='LEFT')
            tbl.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#f0f0f0")),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor("#333333")),
                ('ALIGN', (0, 0), (0, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('GRID', (0, 0), (-1, -1), 0.25, colors.HexColor("#DDDDDD")),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('LEFTPADDING', (0,0), (-1,-1), 6),
                ('RIGHTPADDING', (0,0), (-1,-1), 6),
            ]))
            story.append(tbl)
        else:
            story.append(Paragraph("<i>No sources available</i>", small_style))

        # Build PDF
        doc.build(story)

        buffer.seek(0)
        filename = payload.get("filename") or "account_plan.pdf"
        headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
        return StreamingResponse(buffer, media_type="application/pdf", headers=headers)

    except Exception as e:
        logger.exception("export_pdf failed: %s", e)
        return JSONResponse(status_code=500, content={"error": "export_pdf_failed", "detail": str(e)})

@app.post("/api/chat")
async def api_chat(payload: Dict[str, Any]):
    """
    Q/A chat about the existing plan.
    Uses ChatAgent to answer questions grounded ONLY in the plan.
    """
    try:
        question = payload.get("question")
        plan = payload.get("plan")

        if not question:
            return JSONResponse(status_code=400, content={"error": "missing_question"})
        if not plan:
            return JSONResponse(status_code=400, content={"error": "missing_plan"})

        # Import ChatAgent only where needed (lazy load)
        from agent.chat_agent import ChatAgent
        chat_agent = ChatAgent()

        answer = chat_agent.answer(question, plan)
        return JSONResponse(status_code=200, content={"answer": answer})

    except Exception as e:
        logger.exception("api_chat failed: %s", e)
        return JSONResponse(status_code=500, content={"error": "chat_failed", "detail": str(e)})

if __name__ == "__main__":
    logger.info("Starting server on http://0.0.0.0:8000")
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
