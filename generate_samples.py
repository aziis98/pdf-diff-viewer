import random
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet


def get_lorem_text(sentences=8):
    lorem_base = [
        "Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
        "Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.",
        "Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat.",
        "Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur.",
        "Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.",
        "Sed ut perspiciatis unde omnis iste natus error sit voluptatem accusantium doloremque laudantium.",
        "Totam rem aperiam, eaque ipsa quae ab illo inventore veritatis et quasi architecto beatae vitae dicta sunt explicabo.",
        "Nemo enim ipsam voluptatem quia voluptas sit aspernatur aut odit aut fugit.",
        "Neque porro quisquam est, qui dolorem ipsum quia dolor sit amet, consectetur, adipisci velit.",
        "Quis autem vel eum iure reprehenderit qui in ea voluptate velit esse quam nihil molestiae.",
        "At vero eos et accusamus et iusto odio dignissimos ducimus qui blanditiis praesentium voluptatum.",
        "Et harum quidem rerum facilis est et expedita distinctio. Nam libero tempore, cum soluta nobis.",
        "Temporibus autem quibusdam et aut officiis debitis aut rerum necessitatibus saepe eveniet ut et voluptates.",
        "Itaque earum rerum hic tenetur a sapiente delectus, ut aut reiciendis voluptatibus maiores alias.",
    ]
    return " ".join(random.choices(lorem_base, k=sentences))


def generate_pdf_flow(filename, paragraphs_data):
    doc = SimpleDocTemplate(
        filename,
        pagesize=letter,
        leftMargin=72,
        rightMargin=72,
        topMargin=72,
        bottomMargin=72,
    )
    styles = getSampleStyleSheet()
    styles["Normal"].leading = 16  # Increased line height
    styles["Heading1"].leading = 22  # Proportional increase for headers

    flowables = []
    for item in paragraphs_data:
        if item["type"] == "header":
            flowables.append(Paragraph(item["text"], styles["Heading1"]))
            flowables.append(Spacer(1, 12))
        elif item["type"] == "paragraph":
            flowables.append(Paragraph(item["text"], styles["Normal"]))
            flowables.append(Spacer(1, 12))
        elif item["type"] == "pagebreak":
            flowables.append(PageBreak())

    doc.build(flowables)


# Define document structure
sections = [
    "Executive Summary",
    "Introduction",
    "Current Landscape",
    "Proposed Methodology",
    "Key Findings",
    "Analytical Discussion",
    "Conclusion and Next Steps",
    "Appendices",
]

base_data = []
for sec in sections:
    base_data.append({"type": "header", "text": sec})
    for _ in range(random.randint(4, 7)):
        base_data.append(
            {"type": "paragraph", "text": get_lorem_text(random.randint(6, 12))}
        )
    # Force a page break every 2 sections, but not after the last one
    if (sections.index(sec) + 1) % 2 == 0 and sec != sections[-1]:
        base_data.append({"type": "pagebreak"})

# Create before.pdf
generate_pdf_flow("examples/before.pdf", base_data)

# Create after.pdf with intentional changes
modified_data = []
for i, item in enumerate(base_data):
    # Chance to delete
    if random.random() < 0.08 and item["type"] == "paragraph":
        continue

    # Chance to modify text
    if random.random() < 0.12 and item["type"] == "paragraph":
        new_item = item.copy()
        new_item["text"] = (
            "<b>[REWRITTEN VERSION]</b> "
            + item["text"][:150]
            + " ... (This section was updated to reflect new data) ... "
            + item["text"][-150:]
        )
        modified_data.append(new_item)
        continue

    modified_data.append(item)

    # Chance to insert new paragraph
    if random.random() < 0.1:
        modified_data.append(
            {"type": "paragraph", "text": "<i>[INSERTED]</i> " + get_lorem_text(10)}
        )

generate_pdf_flow("examples/after.pdf", modified_data)

print("Generated examples/before.pdf and examples/after.pdf using ReportLab.")
