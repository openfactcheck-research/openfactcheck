// Wraps sidebar nav labels that match "ClassName kind" in <code> tags.
//
// Why: Material for MkDocs (free tier) strips Markdown from nav labels, so
// a page titled "# `TokenVerifier` protocol" shows up in the sidebar as
// plain "TokenVerifier protocol". This script scans labels, finds ones that
// match the convention, and adds <code> styling for the class name portion.
//
// Convention: the first word is an identifier (CamelCase or UPPER_SNAKE),
// followed by one of the kind nouns below. Labels that don't match are
// left as-is.

const KIND_WORDS = /^([A-Z][A-Za-z0-9_]+)\s+(protocol|class|module|enum|function|method|exception|constant)$/;

function styleNavLabels() {
    document.querySelectorAll(".md-nav__link .md-ellipsis").forEach((el) => {
        // Skip already-processed labels (cheap idempotency).
        if (el.querySelector("code")) return;
        const text = el.textContent.trim();
        const match = text.match(KIND_WORDS);
        if (match) {
            el.innerHTML = `<code>${match[1]}</code> ${match[2]}`;
        }
    });
}

// Re-run on every Material page navigation (instant mode), fall back to
// DOMContentLoaded when Material's observables aren't available.
if (typeof document$ !== "undefined") {
    document$.subscribe(styleNavLabels);
} else {
    document.addEventListener("DOMContentLoaded", styleNavLabels);
}
