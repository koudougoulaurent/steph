"""
Exportateur PDF direct pour les listes d'incidents environnementaux.
Utilise ReportLab avec BytesIO — aucun fichier temporaire sur disque.
"""

from io import BytesIO
from datetime import datetime

# ──────────────── Helpers internes ────────────────────────────────────────────

def _build_doc_and_styles(titre: str):
    """Prépare le document ReportLab et les styles communs."""
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate

    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=landscape(A4),
        rightMargin=1.5 * cm,
        leftMargin=1.5 * cm,
        topMargin=2 * cm,
        bottomMargin=1.5 * cm,
        title=titre,
    )

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name='TitreDoc',
        parent=styles['Heading1'],
        fontSize=16,
        spaceAfter=6,
        textColor=colors.HexColor('#1a472a'),
    ))
    styles.add(ParagraphStyle(
        name='SousTitre',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.grey,
        spaceAfter=14,
    ))
    styles.add(ParagraphStyle(
        name='Pied',
        parent=styles['Normal'],
        fontSize=7,
        textColor=colors.grey,
    ))
    return buf, doc, styles


def _table_style_base(colors_lib):
    """Style de tableau commun à tous les exports."""
    colors = colors_lib
    from reportlab.platypus import TableStyle
    return TableStyle([
        ('BACKGROUND',  (0, 0), (-1, 0), colors.HexColor('#1a472a')),
        ('TEXTCOLOR',   (0, 0), (-1, 0), colors.white),
        ('FONTNAME',    (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE',    (0, 0), (-1, 0), 8),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
        ('TOPPADDING',  (0, 0), (-1, 0), 6),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f4f8f4')]),
        ('FONTNAME',    (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE',    (0, 1), (-1, -1), 7),
        ('TOPPADDING',  (0, 1), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 4),
        ('GRID',        (0, 0), (-1, -1), 0.4, colors.HexColor('#cccccc')),
        ('VALIGN',      (0, 0), (-1, -1), 'MIDDLE'),
    ])


def _build_story(styles, titre: str, sous_titre: str, table_element):
    """Construit la liste d'éléments ReportLab."""
    from reportlab.platypus import Paragraph, Spacer, HRFlowable
    from reportlab.lib import colors

    story = [
        Paragraph(titre, styles['TitreDoc']),
        Paragraph(sous_titre, styles['SousTitre']),
        HRFlowable(width='100%', thickness=1, color=colors.HexColor('#1a472a'), spaceAfter=10),
        table_element,
        Spacer(1, 10),
        Paragraph(
            f"Généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')} — VégéSuivi Pro",
            styles['Pied']
        ),
    ]
    return story


# ──────────────── Feux de brousse ─────────────────────────────────────────────

def export_feux_pdf(feux_liste) -> bytes:
    """
    Génère un PDF listant tous les feux de brousse.
    :param feux_liste: liste de FeuxBrousse
    :return: bytes du PDF
    """
    from reportlab.platypus import Table
    from reportlab.lib import colors
    from reportlab.lib.units import cm

    buf, doc, styles = _build_doc_and_styles('Export Feux de Brousse')

    headers = ['Référence', 'Date debut', 'Zone', 'Village proche',
               'Superficie (ha)', 'Intensité', 'Cause', 'Impact faune', 'Statut', 'Signalé par']

    data = [headers]
    for f in feux_liste:
        data.append([
            f.reference or '',
            f.date_debut.strftime('%d/%m/%Y') if f.date_debut else '',
            f.zone or '',
            f.village_proche or '',
            f"{f.superficie_brulee_ha or 0:.1f}",
            f.intensite or '',
            f.cause or '',
            f.impact_faune or '',
            f.statut or '',
            f.signale_par or '',
        ])

    col_widths = [2.6*cm, 2.2*cm, 3*cm, 3*cm, 2.2*cm, 2*cm, 3*cm, 2.8*cm, 2*cm, 3*cm]
    table = Table(data, colWidths=col_widths, repeatRows=1)
    table.setStyle(_table_style_base(colors))

    sous = f"{len(feux_liste)} enregistrement(s) — Export complet"
    story = _build_story(styles, 'Feux de Brousse', sous, table)
    doc.build(story)
    return buf.getvalue()


# ──────────────── Sites vulnérables ───────────────────────────────────────────

def export_sites_pdf(sites_liste) -> bytes:
    """
    Génère un PDF listant tous les sites vulnérables.
    :param sites_liste: liste de SiteVulnerable
    :return: bytes du PDF
    """
    from reportlab.platypus import Table
    from reportlab.lib import colors
    from reportlab.lib.units import cm

    buf, doc, styles = _build_doc_and_styles('Export Sites Vulnérables')

    headers = ['Référence', 'Nom', 'Type', 'Zone', 'Localité',
               'Superficie (ha)', 'Vulnérabilité', 'Score /100', 'Surveillance', 'Statut']

    data = [headers]
    for s in sites_liste:
        data.append([
            s.reference or '',
            (s.nom or '')[:35],
            s.type_site or '',
            s.zone or '',
            s.localite or '',
            f"{s.superficie_ha or 0:.1f}",
            s.niveau_vulnerabilite or '',
            str(s.score_vulnerabilite or 0),
            s.frequence_surveillance or '',
            s.statut or '',
        ])

    col_widths = [2.2*cm, 4*cm, 2.8*cm, 2.5*cm, 2.5*cm, 2.5*cm, 2.5*cm, 1.8*cm, 2.8*cm, 1.8*cm]
    table = Table(data, colWidths=col_widths, repeatRows=1)
    table.setStyle(_table_style_base(colors))

    sous = f"{len(sites_liste)} site(s) — Export complet"
    story = _build_story(styles, 'Sites Vulnérables', sous, table)
    doc.build(story)
    return buf.getvalue()


# ──────────────── Indicateurs de braconnage ───────────────────────────────────

def export_braconnage_pdf(indicateurs_liste) -> bytes:
    """
    Génère un PDF listant tous les indicateurs de braconnage.
    :param indicateurs_liste: liste de IndicateurBraconnage
    :return: bytes du PDF
    """
    from reportlab.platypus import Table
    from reportlab.lib import colors
    from reportlab.lib.units import cm

    buf, doc, styles = _build_doc_and_styles('Export Indicateurs de Braconnage')

    headers = ['Référence', 'Date constat', 'Type', 'Zone', 'Localité',
               'Espèces', 'Gravité', 'Saisies', 'Arrestations', 'Statut', 'Signalé par']

    data = [headers]
    for b in indicateurs_liste:
        data.append([
            b.reference or '',
            b.date_constat.strftime('%d/%m/%Y') if b.date_constat else '',
            b.type_indicateur or '',
            b.zone or '',
            b.localite or '',
            (b.especes_concernees or '')[:25],
            b.niveau_gravite or '',
            'Oui' if b.saisies_effectuees else 'Non',
            str(b.arrestations or 0),
            b.statut or '',
            b.signale_par or '',
        ])

    col_widths = [2.4*cm, 2.2*cm, 2.8*cm, 2.5*cm, 2.5*cm, 3*cm, 2*cm, 1.6*cm, 2*cm, 1.8*cm, 2.5*cm]
    table = Table(data, colWidths=col_widths, repeatRows=1)
    table.setStyle(_table_style_base(colors))

    sous = f"{len(indicateurs_liste)} indicateur(s) — Export complet"
    story = _build_story(styles, 'Indicateurs de Braconnage', sous, table)
    doc.build(story)
    return buf.getvalue()


# ──────────────── Observations terrain ────────────────────────────────────────

def export_observations_pdf(observations_liste) -> bytes:
    """
    Génère un PDF listant toutes les observations terrain.
    :param observations_liste: liste de ObservationTerrain
    :return: bytes du PDF
    """
    from reportlab.platypus import Table
    from reportlab.lib import colors
    from reportlab.lib.units import cm

    buf, doc, styles = _build_doc_and_styles('Export Observations Terrain')

    headers = ['Référence', 'Date', 'Catégorie', 'Titre', 'Zone',
               'État général', 'Alerte', 'Agent', 'Campagne', 'Validée']

    data = [headers]
    for o in observations_liste:
        agent_nom = o.agent.nom if o.agent else ''
        campagne_ref = o.campagne.reference if o.campagne else ''
        data.append([
            o.reference or '',
            o.date_observation.strftime('%d/%m/%Y') if o.date_observation else '',
            o.categorie or '',
            (o.titre or (o.description or '')[:40] or '')[:40],
            o.zone or '',
            o.etat_general or '',
            o.niveau_alerte or '',
            agent_nom[:20],
            campagne_ref,
            'Oui' if o.validee else 'Non',
        ])

    col_widths = [2.4*cm, 2.2*cm, 2.2*cm, 4.5*cm, 2.5*cm, 2*cm, 2*cm, 2.8*cm, 2.2*cm, 1.5*cm]
    table = Table(data, colWidths=col_widths, repeatRows=1)
    table.setStyle(_table_style_base(colors))

    sous = f"{len(observations_liste)} observation(s) — Export complet"
    story = _build_story(styles, 'Observations Terrain', sous, table)
    doc.build(story)
    return buf.getvalue()
