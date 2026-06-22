"""
AuditLens — Autonomous QA / UX Auditor
Backend: FastAPI + SQLAlchemy + SQLite
"""
import os
import random
import hashlib
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, HttpUrl
from sqlalchemy import create_engine, Column, Integer, String, Float, Text, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session

# ── Database ────────────────────────────────────────────────────
DB_PATH = os.path.join(os.path.dirname(__file__), "auditlens.db")
engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


class Audit(Base):
    __tablename__ = "audits"
    id = Column(Integer, primary_key=True, autoincrement=True)
    url = Column(String(2048), nullable=False)
    status = Column(String(20), default="pending")  # pending, running, completed, failed
    overall_score = Column(Float, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    scores = relationship("AuditScore", back_populates="audit", cascade="all, delete")
    issues = relationship("AuditIssue", back_populates="audit", cascade="all, delete")


class AuditScore(Base):
    __tablename__ = "audit_scores"
    id = Column(Integer, primary_key=True, autoincrement=True)
    audit_id = Column(Integer, ForeignKey("audits.id"))
    category = Column(String(50))
    score = Column(Float)
    max_score = Column(Float, default=100)
    audit = relationship("Audit", back_populates="scores")


class AuditIssue(Base):
    __tablename__ = "audit_issues"
    id = Column(Integer, primary_key=True, autoincrement=True)
    audit_id = Column(Integer, ForeignKey("audits.id"))
    severity = Column(String(20))  # critical, warning, info, success
    category = Column(String(50))
    title = Column(String(500))
    description = Column(Text)
    suggestion = Column(Text)
    element = Column(String(500), nullable=True)
    audit = relationship("Audit", back_populates="issues")


Base.metadata.create_all(engine)


# ── Audit Engine ──────────────────────────────────────────────────
CATEGORIES = ["accessibility", "performance", "seo", "best_practices", "mobile"]

ACCESSIBILITY_ISSUES = [
    ("Contrast ratio too low", "Text contrast ratio is 2.8:1, below the 4.5:1 WCAG AA minimum.", "Increase text contrast to at least 4.5:1 ratio.", "color.css:14", "critical"),
    ("Missing alt text on images", "7 images found without alt attributes.", "Add descriptive alt text to all informative images.", "index.html:234", "warning"),
    ("Form inputs missing labels", "3 form inputs lack associated <label> elements.", "Add <label> elements with for attributes matching input ids.", "contact.html:56", "critical"),
    ("Skip navigation missing", "No skip-to-content link found for keyboard users.", "Add a skip navigation link as the first focusable element.", "header.html:1", "warning"),
    ("Focus indicators removed", "CSS outline: none found on interactive elements without replacement.", "Provide visible focus indicators for all interactive elements.", "global.css:223", "warning"),
    ("ARIA roles misused", "role='button' found on a <div> without keyboard event handlers.", "Use native <button> elements or add proper keyboard support.", "app.js:145", "critical"),
    ("Heading hierarchy broken", "Skipped from h1 to h3 without h2 in between.", "Maintain proper heading hierarchy (h1 → h2 → h3).", "blog.html:12", "info"),
    ("Touch targets too small", "4 clickable elements are smaller than 44x44px.", "Ensure all touch targets are at least 44x44px.", "nav.css:45", "warning"),
]

PERFORMANCE_ISSUES = [
    ("Unoptimized images", "12 images total 8.4MB, potential savings of 6.2MB.", "Compress images using WebP/AVIF and implement lazy loading.", "images/hero.png", "critical"),
    ("Render-blocking resources", "3 CSS and 5 JS files block first paint.", "Defer non-critical JS and inline critical CSS.", "index.html:8", "warning"),
    ("No text compression", "HTML resources served without gzip or brotli compression.", "Enable gzip/brotli compression on your server.", "server config", "warning"),
    ("Large DOM tree", "DOM has 2,847 nodes (recommended < 1,500).", "Simplify HTML structure and remove unnecessary wrappers.", "index.html", "info"),
    ("No cache policy", "Static assets missing Cache-Control headers.", "Set Cache-Control: max-age=31536000 for static assets.", "server config", "warning"),
    ("JavaScript execution time", "Main thread blocked for 1.2s during script execution.", "Break up long tasks and use requestIdleCallback for non-critical work.", "app.js:234", "critical"),
    ("No lazy loading", "Desktop-only images load on mobile viewports.", "Add loading='lazy' to below-the-fold images.", "gallery.html:67", "info"),
    ("Unminified CSS", "3 CSS files are unminified (saves ~180KB).", "Minify CSS for production builds.", "styles/main.css", "info"),
]

SEO_ISSUES = [
    ("Missing meta description", "No <meta name=\"description\"> tag found.", "Add a unique meta description (150-160 chars) to each page.", "index.html:5", "critical"),
    ("Title tag too short", "Title tag is 12 characters (recommended 50-60).", "Write descriptive title tags between 50-60 characters.", "index.html:4", "warning"),
    ("No Open Graph tags", "Missing og:title, og:description, og:image.", "Add Open Graph meta tags for social sharing.", "index.html:5", "warning"),
    ("Missing canonical URL", "No <link rel=\"canonical\"> tag.", "Add canonical URLs to prevent duplicate content.", "index.html:5", "info"),
    ("No robots.txt", "robots.txt file not found.", "Create a robots.txt in the root directory.", "/", "info"),
    ("No sitemap.xml", "XML sitemap not detected.", "Generate and submit an XML sitemap.", "/", "info"),
    ("Broken internal links", "3 internal links return 404 errors.", "Fix or remove broken internal links.", "footer.html:23", "warning"),
    ("No structured data", "No JSON-LD or microdata found.", "Add Schema.org structured data for key entities.", "index.html:10", "info"),
]

BEST_PRACTICES_ISSUES = [
    ("Mixed content detected", "HTTPS page loads 2 resources over HTTP.", "Update all resource URLs to use HTTPS.", "index.html:34", "critical"),
    ("Console errors", "4 JavaScript errors in console during page load.", "Fix JavaScript exceptions shown in browser console.", "app.js:89", "warning"),
    ("No Content-Security-Policy", "Missing CSP header increases XSS risk.", "Implement a Content-Security-Policy header.", "server config", "info"),
    ("Insecure cookies", "Cookies missing Secure and HttpOnly flags.", "Set Secure, HttpOnly, and SameSite attributes on cookies.", "server config", "warning"),
    ("Deprecated APIs", "2 deprecated JavaScript APIs detected.", "Replace deprecated APIs with modern alternatives.", "utils.js:45", "info"),
    ("No error pages", "Custom 404 page not configured.", "Create custom error pages (404, 500, 403).", "/", "info"),
]

MOBILE_ISSUES = [
    ("Viewport not set", "No <meta name=\"viewport\"> tag found.", "Add viewport meta tag: width=device-width, initial-scale=1.", "index.html:5", "critical"),
    ("Text too small on mobile", "Base font size is 10px on mobile layouts.", "Use minimum 16px base font size for mobile.", "mobile.css:12", "warning"),
    ("Horizontal overflow detected", "Content overflows viewport by 48px on 375px screens.", "Fix overflowing elements with max-width: 100% or overflow-x: hidden.", "index.html:123", "critical"),
    ("Fixed-width elements", "3 elements use fixed widths wider than mobile viewport.", "Use responsive units (%, vw, max-width) instead of fixed pixels.", "layout.css:78", "warning"),
    ("No touch feedback", "Buttons lack visual feedback on touch interactions.", "Add :active states and transition effects for touch.", "components.css:34", "info"),
]


def generate_audit(url: str) -> dict:
    """Generate a realistic audit report for a given URL."""
    # Use URL hash for deterministic but varied results
    url_hash = int(hashlib.md5(url.encode()).hexdigest()[:8], 16)
    random.seed(url_hash)

    num_issues = random.randint(8, 20)
    all_issues = []
    category_scores = {}

    # Pick issues from each category
    for cat_name, issues_list in [
        ("accessibility", ACCESSIBILITY_ISSUES),
        ("performance", PERFORMANCE_ISSUES),
        ("seo", SEO_ISSUES),
        ("best_practices", BEST_PRACTICES_ISSUES),
        ("mobile", MOBILE_ISSUES),
    ]:
        cat_issues = random.sample(issues_list, min(random.randint(2, 4), len(issues_list)))
        penalty = sum({"critical": 15, "warning": 8, "info": 2, "success": 0}[i[4]] for i in cat_issues)
        score = max(30, 100 - penalty + random.randint(-5, 5))
        category_scores[cat_name] = min(100, max(0, score))
        for issue in cat_issues:
            all_issues.append({
                "severity": issue[4],
                "category": cat_name,
                "title": issue[0],
                "description": issue[1],
                "suggestion": issue[2],
                "element": issue[3],
            })

    # Overall score is weighted average
    weights = {"accessibility": 0.25, "performance": 0.3, "seo": 0.2, "best_practices": 0.1, "mobile": 0.15}
    overall = sum(category_scores[c] * w for c, w in weights.items())
    overall = min(100, max(0, overall + random.randint(-5, 5)))

    return {
        "overall_score": round(overall, 1),
        "category_scores": {k: round(v, 1) for k, v in category_scores.items()},
        "issues": all_issues,
        "page_info": {
            "title": f"Page at {url}",
            "url": url,
            "language": "en",
            "viewport_set": random.choice([True, False]),
        }
    }


# ── FastAPI App ───────────────────────────────────────────────────
app = FastAPI(title="AuditLens", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Pydantic Models ──────────────────────────────────────────────
class AuditCreate(BaseModel):
    url: str


class AuditResponse(BaseModel):
    id: int
    url: str
    status: str
    overall_score: float
    created_at: str


class AuditDetail(BaseModel):
    id: int
    url: str
    status: str
    overall_score: float
    created_at: str
    category_scores: list
    issues: list
    page_info: dict


# ── API Routes ───────────────────────────────────────────────────
@app.post("/api/audits", response_model=AuditResponse)
def create_audit(body: AuditCreate):
    db: Session = SessionLocal()
    try:
        # Create audit
        audit = Audit(url=body.url, status="running")
        db.add(audit)
        db.flush()

        # Generate audit
        result = generate_audit(body.url)

        audit.status = "completed"
        audit.overall_score = result["overall_score"]

        for cat, score in result["category_scores"].items():
            db.add(AuditScore(audit_id=audit.id, category=cat, score=score, max_score=100))

        for issue in result["issues"]:
            db.add(AuditIssue(
                audit_id=audit.id,
                severity=issue["severity"],
                category=issue["category"],
                title=issue["title"],
                description=issue["description"],
                suggestion=issue["suggestion"],
                element=issue.get("element", ""),
            ))

        db.commit()
        return AuditResponse(
            id=audit.id,
            url=audit.url,
            status=audit.status,
            overall_score=audit.overall_score,
            created_at=audit.created_at.isoformat(),
        )
    finally:
        db.close()


@app.get("/api/audits", response_model=list[AuditResponse])
def list_audits():
    db: Session = SessionLocal()
    try:
        audits = db.query(Audit).order_by(Audit.created_at.desc()).limit(50).all()
        return [AuditResponse(
            id=a.id, url=a.url, status=a.status,
            overall_score=a.overall_score, created_at=a.created_at.isoformat(),
        ) for a in audits]
    finally:
        db.close()


@app.get("/api/audits/{audit_id}")
def get_audit(audit_id: int):
    db: Session = SessionLocal()
    try:
        audit = db.query(Audit).filter_by(id=audit_id).first()
        if not audit:
            raise HTTPException(status_code=404, detail="Audit not found")
        scores = [{"category": s.category, "score": s.score, "max_score": s.max_score} for s in audit.scores]
        issues = [{
            "severity": i.severity, "category": i.category,
            "title": i.title, "description": i.description,
            "suggestion": i.suggestion, "element": i.element or "",
        } for i in audit.issues]
        return {
            "id": audit.id, "url": audit.url, "status": audit.status,
            "overall_score": audit.overall_score, "created_at": audit.created_at.isoformat(),
            "category_scores": scores, "issues": issues,
            "page_info": {"title": f"Page at {audit.url}", "url": audit.url, "language": "en"},
        }
    finally:
        db.close()


@app.delete("/api/audits/{audit_id}")
def delete_audit(audit_id: int):
    db: Session = SessionLocal()
    try:
        audit = db.query(Audit).filter_by(id=audit_id).first()
        if not audit:
            raise HTTPException(status_code=404, detail="Audit not found")
        db.delete(audit)
        db.commit()
        return {"ok": True}
    finally:
        db.close()


# Serve frontend
from fastapi.responses import HTMLResponse
import os as _os
_frontend_path = _os.path.join(_os.path.dirname(__file__), "..", "frontend", "index.html")

@app.get("/api/health")
def health():
    return {"ok": True, "app": "AuditLens", "version": "1.0.0"}

@app.get("/", response_class=HTMLResponse)
def serve_frontend():
    with open(_frontend_path) as f:
        return HTMLResponse(content=f.read())


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9002)
