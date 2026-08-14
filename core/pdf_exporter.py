import io
from typing import Optional
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from core.storyboard_engine import StoryboardProject

class StoryboardPDFExporter:
    @staticmethod
    def export_pdf(storyboard: StoryboardProject) -> bytes:
        """Genera un archivo PDF profesional del Storyboard completo."""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=landscape(letter),
            leftMargin=36,
            rightMargin=36,
            topMargin=36,
            bottomMargin=36
        )

        styles = getSampleStyleSheet()
        
        # Estilos tipográficos personalizados
        title_style = ParagraphStyle(
            'StoryTitle',
            parent=styles['Heading1'],
            fontName='Helvetica-Bold',
            fontSize=22,
            leading=26,
            textColor=colors.HexColor('#0f172a'),
            spaceAfter=6
        )
        
        subtitle_style = ParagraphStyle(
            'StorySubtitle',
            parent=styles['Normal'],
            fontName='Helvetica-Oblique',
            fontSize=11,
            leading=15,
            textColor=colors.HexColor('#475569'),
            spaceAfter=14
        )

        badge_style = ParagraphStyle(
            'BadgeStyle',
            fontName='Helvetica-Bold',
            fontSize=8.5,
            leading=11,
            textColor=colors.HexColor('#1e40af'),
            alignment=TA_CENTER
        )

        shot_title_style = ParagraphStyle(
            'ShotTitle',
            fontName='Helvetica-Bold',
            fontSize=11,
            leading=14,
            textColor=colors.HexColor('#0f172a')
        )

        body_style = ParagraphStyle(
            'Body',
            fontName='Helvetica',
            fontSize=9,
            leading=12,
            textColor=colors.HexColor('#1e293b')
        )

        dialogue_style = ParagraphStyle(
            'Dialogue',
            fontName='Helvetica-Oblique',
            fontSize=9,
            leading=12,
            textColor=colors.HexColor('#0369a1')
        )

        label_style = ParagraphStyle(
            'Label',
            fontName='Helvetica-Bold',
            fontSize=8,
            leading=10,
            textColor=colors.HexColor('#64748b')
        )

        story = []

        # Header Principal
        story.append(Paragraph(f"STORYBOARD CINEMATOGRÁFICO: {storyboard.title.upper()}", title_style))
        story.append(Paragraph(f"<b>Logline:</b> {storyboard.logline}", subtitle_style))
        
        # Meta info bar en tabla
        meta_data = [
            [
                Paragraph(f"<b>Género & Tono:</b> {storyboard.genre_and_tone}", body_style),
                Paragraph(f"<b>Estilo Visual:</b> {storyboard.visual_style}", body_style),
                Paragraph(f"<b>Aspect Ratio:</b> {storyboard.aspect_ratio}", body_style),
                Paragraph(f"<b>Duración Total:</b> ~{storyboard.target_duration_seconds}s ({len(storyboard.shots)} planos)", body_style)
            ]
        ]
        meta_table = Table(meta_data, colWidths=[200, 200, 150, 170])
        meta_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f1f5f9')),
            ('PADDING', (0,0), (-1,-1), 8),
            ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#cbd5e1')),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ]))
        story.append(meta_table)
        story.append(Spacer(1, 14))

        # Guía de Personajes si existe
        if storyboard.character_bibles:
            story.append(Paragraph("<b>GUÍA DE CONSISTENCIA DE PERSONAJES:</b>", label_style))
            char_text = " • ".join(storyboard.character_bibles)
            story.append(Paragraph(char_text, body_style))
            story.append(Spacer(1, 14))

        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#cbd5e1'), spaceBefore=4, spaceAfter=14))

        # Renderizar cada toma en formato de tarjeta de producción
        for shot in storyboard.shots:
            shot_content = [
                # Fila 1: Header de toma
                [
                    Paragraph(f"TOMA #{shot.shot_number}", badge_style),
                    Paragraph(f"<b>{shot.shot_title}</b>", shot_title_style),
                    Paragraph(f"<b>Tipo:</b> {shot.shot_type}", body_style),
                    Paragraph(f"<b>Duración:</b> {shot.estimated_duration_sec}s", body_style)
                ],
                # Fila 2: Detalles Técnicos y visuales
                [
                    Paragraph(f"<b>CÁMARA & LUZ:</b>", label_style),
                    Paragraph(f"<b>Movimiento:</b> {shot.camera_movement}<br/><b>Iluminación/Atmósfera:</b> {shot.lighting_and_atmosphere}", body_style),
                    Paragraph(f"<b>ACCIÓN VISUAL:</b><br/>{shot.visual_action}", body_style),
                    Paragraph(f"<b>DIÁLOGO / LOCUCIÓN:</b><br/>\"{shot.dialogue_or_voiceover}\"<br/><br/><b>SFX:</b> {shot.sound_effects_and_music}", dialogue_style)
                ]
            ]
            
            shot_table = Table(
                shot_content,
                colWidths=[80, 200, 240, 200]
            )
            shot_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#e2e8f0')),
                ('BACKGROUND', (0,1), (-1,1), colors.HexColor('#ffffff')),
                ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#94a3b8')),
                ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
                ('PADDING', (0,0), (-1,-1), 6),
                ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ]))

            story.append(KeepTogether([shot_table, Spacer(1, 10)]))

        doc.build(story)
        buffer.seek(0)
        return buffer.getvalue()
