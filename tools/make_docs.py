"""Build illustrated bilingual PDF/HTML manuals and the development report."""
from pathlib import Path
import sys,re,html,json,math
from xml.sax.saxutils import escape
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root))
from reportlab.pdfgen import canvas
from reportlab.platypus import (SimpleDocTemplate,Paragraph,Spacer,Image,PageBreak,Table,TableStyle,KeepTogether)
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4,landscape
from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from PIL import Image as PILImage
from voxdose.i18n import METRICS,metric
from voxdose import AUTHOR,AFFILIATION

docs=root/'docs';images=docs/'images';qa=root/'validation'/'documents';qa.mkdir(parents=True,exist_ok=True)
import shutil
shutil.copy2(root/'voxdose'/'assets'/'icon.png',images/'icon.png')
for name,file in [('Vox','segoeui.ttf'),('VoxBold','segoeuib.ttf'),('VoxItalic','segoeuii.ttf')]:
    pdfmetrics.registerFont(TTFont(name,'C:/Windows/Fonts/'+file))
pdfmetrics.registerFontFamily('Vox',normal='Vox',bold='VoxBold',italic='VoxItalic',boldItalic='VoxBold')
styles=getSampleStyleSheet()
styles.add(ParagraphStyle(name='VBody',fontName='Vox',fontSize=10,leading=14,textColor=colors.HexColor('#294156'),spaceAfter=8))
styles.add(ParagraphStyle(name='VSmall',parent=styles['VBody'],fontSize=8.2,leading=11,spaceAfter=5))
styles.add(ParagraphStyle(name='VHead',fontName='VoxBold',fontSize=21,leading=26,textColor=colors.HexColor('#0B3548'),spaceAfter=14,keepWithNext=True))
styles.add(ParagraphStyle(name='VSub',fontName='VoxBold',fontSize=13,leading=17,textColor=colors.HexColor('#087F8C'),spaceBefore=10,spaceAfter=7,keepWithNext=True))
styles.add(ParagraphStyle(name='VCover',fontName='VoxBold',fontSize=40,leading=45,textColor=colors.HexColor('#0B3548'),spaceAfter=16))
styles.add(ParagraphStyle(name='VCell',fontName='Vox',fontSize=8.1,leading=11,textColor=colors.HexColor('#294156')))

def normalize(s):return s.replace('–','-').replace('—','-').replace('\u2011','-')
def markup(text):
    text=escape(normalize(text))
    text=re.sub(r'\[([^\]]+)\]\((https?://[^)]+)\)',r'<a href="\2" color="#087F8C">\1</a>',text)
    text=re.sub(r'\*\*(.*?)\*\*',r'<b>\1</b>',text)
    text=re.sub(r'`([^`]+)`',r'<font color="#087F8C">\1</font>',text)
    return text
def para(text,style='VBody'):return Paragraph(markup(text),styles[style])
def table(rows,widths,header=True,compact=False):
    data=[[para(str(c),'VCell') for c in row] for row in rows]
    t=Table(data,colWidths=widths,repeatRows=1 if header else 0,hAlign='LEFT')
    commands=[('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),8),('RIGHTPADDING',(0,0),(-1,-1),8),
              ('TOPPADDING',(0,0),(-1,-1),4 if compact else 7),('BOTTOMPADDING',(0,0),(-1,-1),4 if compact else 7),('LINEBELOW',(0,0),(-1,0),1,colors.HexColor('#087F8C'))]
    for i in range(len(data)):
        if i==0 and header:commands.append(('BACKGROUND',(0,i),(-1,i),colors.HexColor('#DDEFF1')))
        elif i%2:commands.append(('BACKGROUND',(0,i),(-1,i),colors.HexColor('#F3F7FA')))
    t.setStyle(TableStyle(commands));return t

def footer(label):
    def draw(c,doc):
        width,height=doc.pagesize
        c.setFillColor(colors.HexColor('#087F8C'));c.rect(38,height-27,width-76,3,fill=1,stroke=0)
        c.setFont('Vox',8);c.setFillColor(colors.HexColor('#64788A'))
        c.drawString(38,height-43,'VoxDose 2.0   /   '+label)
        c.setStrokeColor(colors.HexColor('#DDE6EE'));c.line(38,32,width-38,32)
        c.drawString(38,19,AUTHOR+'  |  UFMG  |  15/11/2026')
        c.drawRightString(width-38,19,str(doc.page))
    return draw

def crop_image(name):
    path=images/name
    img=PILImage.open(path)
    # Remove repeating banner but keep tabs and the entire active page.
    img=img.crop((16,200,img.width-16,img.height-30))
    dest=qa/(path.stem+'_content.png');img.save(dest)
    return dest

def image_flow(path,maxw,maxh):
    im=PILImage.open(path);scale=min(maxw/im.width,maxh/im.height)
    return Image(str(path),width=im.width*scale,height=im.height*scale,hAlign='CENTER')

def manual(language):
    pt=language=='pt_BR';prefix='pt' if pt else 'en'
    T=lambda a,b:a if pt else b
    name='Manual_pt_BR' if pt else 'Manual_en';pages=[]
    pages.append({'title':T('Manual do usuário','User manual'),'cover':True,'paragraphs':[
        T('Exposição vocal, comparação de sessões e registro perceptivo.','Vocal exposure, session comparison and perceptual records.'),
        AUTHOR+' - '+AFFILIATION,
        T('Adaptação dos códigos originais de Pasquale Bottalico. Desenvolvimento e modernização da versão 2.0 por Tiago Lima Bicalho Cruz.','Adapted from original code by Pasquale Bottalico. Version 2.0 development and modernization by Tiago Lima Bicalho Cruz.'),
        T('As telas deste manual utilizam sinais e avaliações artificiais, identificados como Synthetic/DEMO. Não são dados clínicos ou valores normativos.','Screens in this manual use artificial signals and ratings identified as Synthetic/DEMO. They are not clinical data or normative values.') ]})
    pages.append({'title':T('01 / Começar e analisar','01 / Start and analyze'),'paragraphs':[
        T('No Windows, use o instalador NSIS e abra VoxDose pelo menu Iniciar, ou execute a cópia portátil VoxDose-2.0.exe. Python já está incluído. O idioma inicial é inglês; para português, use Settings > Language > Português brasileiro > Apply preferences. Adicione ou arraste WAV/FLAC, identifique participante, tarefa e dispositivo e configure canal, calibração e F0 antes de analisar.','On Windows, use the NSIS installer and open VoxDose from the Start menu, or run the portable VoxDose-2.0.exe. Python is included. New configurations start in English; Brazilian Portuguese is available in Settings > Language. Add or drop WAV/FLAC, identify participant, task and device, and set channel, calibration and F0 before analysis.'),
        T('O pacote de fontes inclui as sessões artificiais examples/Synthetic_A.voxdose e Synthetic_B.voxdose. Abra-as com Abrir sessão para explorar sem recalcular o áudio. Troque a sessão ativa na barra superior.','The source package includes artificial sessions examples/Synthetic_A.voxdose and Synthetic_B.voxdose. Open them with Open session to explore without recalculating audio. Switch the active session in the top bar.')],
        'image':prefix+'_01.png','caption':T('A fila aceita múltiplos arquivos. Cada análise concluída salva resultados em uma pasta própria.','The queue accepts multiple files. Each completed analysis saves results to its own folder.')})
    pages.append({'title':T('02 / Calibrar a intensidade','02 / Calibrate intensity'),'paragraphs':[
        T('Use uma emissão estável com leitura simultânea do sonômetro. O áudio de calibração e o monitoramento precisam do mesmo canal, ganho e montagem. Evite silêncio, controle automático de ganho e saturação. Escolha A para dBA ou Z para dBZ; não substitua dBC por Z.','Use a steady emission with simultaneous sound level meter reading. Calibration and monitoring need the same channel, gain and setup. Avoid silence, automatic gain control and clipping. Choose A for dBA or Z for dBZ; do not substitute dBC for Z.')],
        'image':prefix+'_calibration.png','caption':T('Microfone aéreo: 1-3 pontos. Distância = boca-sonômetro. Sem calibração: dBFS; Dd/De/Dr indisponíveis.','Air microphone: 1-3 points. Distance = mouth-to-meter. Uncalibrated: dBFS; Dd/De/Dr unavailable.')})
    pages.append({'title':T('03 / Ajustar a detecção','03 / Adjust detection'),'paragraphs':[
        T('Fala: ponto de partida 60-500 Hz; canto: 50-1200 Hz. Ajuste à voz real. A faixa não define gênero. O modelo biomecânico só altera Dd e De; a média combina os dois ramos históricos. Um quadro exige F0 detectada e nível acima do limiar.','Speech: start at 60-500 Hz; singing: 50-1200 Hz. Adapt to the actual voice. The range does not define gender. The biomechanical model only affects Dd and De; the mean combines the historical branches. A frame requires detected F0 and a level above the gate.')],
        'image':prefix+'_detection.png','caption':T('Passe o mouse sobre (i) para ler a explicação, sem clicar nem fechar uma caixa. O detector não separa automaticamente outras pessoas ou artefatos de movimento.','Hover over (i) to read an explanation, with no click or dialog to dismiss. The detector does not automatically separate other speakers or movement artifacts.')})
    pages.append({'title':T('04 / Ler a tabela de doses','04 / Read the dose table'),'paragraphs':[
        T('A tabela separa valor, unidade e método. Busque medidas, ordene pelas colunas e clique duas vezes para ler a descrição. O intervalo calcula apenas o trecho indicado, com ponderação dos quadros parciais. CPPS/HNR preservam suas janelas originais de 5 s.','The table separates value, unit and method. Search measures, sort columns and double-click for a description. The interval computes only the selected segment, weighting partial frames. CPPS/HNR retain their original 5 s windows.')],
        'image':prefix+'_02.png','caption':T('Traço indica medida indisponível. As mensagens acima da tabela contextualizam calibração e qualidade.','A dash means an unavailable measure. Messages above the table provide calibration and quality context.')})
    glossary=list(METRICS.items())
    for i,(a,b) in enumerate([(0,16),(16,30),(30,len(glossary))]):
        rows=[[T('Medida','Measure'),T('Unidade','Unit'),T('Como interpretar','How to interpret')]]
        for key,_ in glossary[a:b]:
            label,unit,description=metric(key,language);rows.append([label,unit,description])
        pages.append({'title':T(f'05 / Guia das medidas ({i+1}/3)',f'05 / Measure guide ({i+1}/3)'),
            'paragraphs':[T('Doses e características acústicas descrevem exposição e comportamento. Não há ponto de corte automático para fadiga, dano ou necessidade de repouso.','Doses and acoustic features describe exposure and behavior. There is no automatic cutoff for fatigue, injury or need for rest.')], 'table':rows})
    pages.append({'title':T('06 / Gráficos em conjunto','06 / Combined charts'),'paragraphs':[
        T('O painel reúne intensidade, F0, CPPS, ciclos acumulados, fonação por janela e distribuições. O eixo é tempo desde o início, em minutos. A média de intensidade é aritmética; o Leq energético está na tabela.','The dashboard combines intensity, F0, CPPS, accumulated cycles, windowed phonation and distributions. Time is minutes from the start. Mean intensity is arithmetic; the energy-based Leq is in the table.')],
        'image':prefix+'_03.png','caption':T('Cinza: pausas ≥0,5 s. Médias só aparecem na fonação e em janelas com ≥5% e ≥0,5 s de fonação. A apresentação preserva os dados e as doses.','Gray: pauses ≥0.5 s. Means appear only during voicing and in windows with ≥5% and ≥0.5 s voicing. Display changes preserve data and doses.')})
    pages.append({'title':T('07 / Gráficos individuais e ampliados','07 / Individual and enlarged charts'),'paragraphs':[
        T('Escolha um dos 13 tipos no seletor e use Abrir separado. Há HNR, envelope RMS e doses acumuladas Dd/De/Dr, além do painel. RMS é um envelope por quadro, não a forma de onda bruta. Use a barra para zoom, deslocamento e salvar.','Choose one of 13 types in the selector and Open separately. HNR, RMS envelope and accumulated Dd/De/Dr are available in addition to dashboard plots. RMS is a frame envelope, not the raw waveform. Use the toolbar to zoom, pan and save.')],
        'image':prefix+'_separate.png','caption':T('Exportar resultados gera PNG e SVG. A opção de gráficos separados fica em Ajustes.','Export results generates PNG and SVG. Separate figure export is controlled in Settings.')})
    pages.append({'title':T('08 / Comparar gravações longas','08 / Compare long recordings'),'paragraphs':[
        T('Marque pelo menos duas sessões. A primeira é a referência. Atualize a comparação; amplie o gráfico quando precisar de mais espaço. Use eixo absoluto para tempo decorrido ou relativo para alinhar 0-100% da duração.','Select at least two sessions. The first is the reference. Update comparison; enlarge the chart for more space. Use absolute time for elapsed time or relative time to align 0-100% of duration.')],
        'image':prefix+'_04.png','caption':T('Para durações distintas, priorize taxas por hora. Totais e curvas acumuladas dependem do tempo de gravação.','For different durations, prioritize per-hour rates. Totals and cumulative curves depend on recording duration.')})
    pages.append({'title':T('09 / Interpretar diferenças com contexto','09 / Interpret differences in context'),'paragraphs':[
        T('Exemplo: 100 mil ciclos em 1 h e 200 mil em 2 h têm o mesmo valor de 100 mil ciclos por hora. O segundo total é maior, mas a taxa é igual. Consulte ambas as medidas.','Example: 100,000 cycles over 1 h and 200,000 over 2 h both equal 100,000 cycles per hour. The second total is higher, but the rate is equal. Consult both measures.'),
        T('Os deltas exigem participante, tarefa e dispositivo preenchidos e iguais, além de parâmetros e método compatíveis. Uma mensagem explica impedimentos. Valores individuais permanecem visíveis. Esse controle não garante condições experimentais equivalentes.','Deltas require matching, nonempty participant, task and device fields, plus compatible parameters and method. A message explains mismatches. Individual values remain visible. This does not guarantee equivalent experimental conditions.'),
        T('Delta é diferença absoluta, sem teste de significância. Para fonação percentual, a unidade do delta é ponto percentual. O eixo relativo não sincroniza eventos reais, e pausas do detector não demonstram recuperação tecidual.','Delta is an absolute difference, without a significance test. For phonation percentage, delta is in percentage points. Relative time does not synchronize actual events, and detector pauses do not establish tissue recovery.'),
        T('A versão 2.0 corrige cálculos e unidades da versão anterior. Reanalise os áudios originais para comparar versões; não combine automaticamente planilhas antigas e novas.','Version 2.0 corrects earlier calculations and units. Reanalyze original audio for version comparisons; do not automatically pool old and new spreadsheets.')],
        'table':[[T('Verifique','Check'),T('Por quê','Why')],[T('Participante e tarefa','Participant and task'),T('Evitar atribuir diferenças de contexto a mudanças da voz.','Avoid attributing context differences to voice changes.')],[T('Ganho, posição e acoplamento','Gain, placement and coupling'),T('Alterações podem mudar intensidade e medidas espectrais.','Changes can alter intensity and spectral measures.')],[T('Faixa F0, limiar e calibração','F0 bounds, gate and calibration'),T('Afetam seleção de fonação e estimativas físicas.','They affect voicing selection and physical estimates.')],[T('Total e taxas normalizadas','Total and normalized rates'),T('Distinguem duração e intensidade de exposição.','They distinguish exposure duration from exposure intensity.')]]})
    pages.append({'title':T('10 / Registrar esforço e fadiga percebidos','10 / Record perceived effort and fatigue'),'paragraphs':[
        T('O diário registra esforço, fadiga e desconforto de 0 a 10, com data/hora e fuso. Zero = nenhum; dez = máximo imaginável. Classifique antes, após ou acompanhamento. Registros não são calculados pelo áudio e não equivalem ao VFI, Borg ou questionário validado.','The diary records effort, fatigue and discomfort from 0 to 10, with date/time and timezone. Zero = none; ten = maximum imaginable. Label before, after or follow-up. Ratings are not calculated from audio and are not the VFI, Borg or a validated questionnaire.')],
        'image':prefix+'_05.png','caption':T('Adicionar/excluir atualiza a sessão local. Exporte CSV para acompanhar os registros. Dados mostrados são artificiais.','Adding/deleting updates the local session. Export CSV to follow ratings. Shown data are artificial.')})
    pages.append({'title':T('11 / Idioma, aparência e ajuda','11 / Language, appearance and help'),'paragraphs':[
        T('Novas configurações iniciam em inglês. Em Ajustes, selecione português brasileiro ou inglês, tema claro/escuro e tutoriais; aplique as preferências. Passe o mouse sobre (i) para ver a explicação imediatamente: não há clique nem botão OK. Foco pelo teclado também mostra a ajuda. Desativar tutoriais remove (i) e dicas de campos, mantendo o guia e as descrições da tabela. A sessão e os parâmetros são preservados.','New configurations start in English. In Settings, choose Brazilian Portuguese or English, light/dark theme and tutorials, then apply preferences. Hover over (i) for an immediate explanation: no click or OK button is required. Keyboard focus also shows help. Disabling tutorials removes (i) and field tips while retaining the guide and table descriptions. Sessions and parameters are preserved.')],
        'image':prefix+'_06.png','caption':T('Créditos: adaptação dos códigos de Pasquale Bottalico; desenvolvimento 2.0 por Tiago Lima Bicalho Cruz, UFMG.','Credits: adapted from Pasquale Bottalico code; version 2.0 development by Tiago Lima Bicalho Cruz, UFMG.')})
    pages.append({'title':T('12 / Salvar, exportar e reproduzir','12 / Save, export and reproduce'),'paragraphs':[
        T('Após analisar, o programa cria uma pasta em results com sessão, tabelas e metadados. No Windows instalado, os dados ficam em %LOCALAPPDATA%/VoxDose; no portátil, ao lado do EXE. Abra a pasta pelo botão em Ajustes. A desinstalação preserva os dados. Exportar resultados cria outro conjunto com gráficos e identificador próprio; Salvar sessão permite escolher outro arquivo.','After analysis, the program creates a results folder with session, tables and metadata. Installed Windows data is stored in %LOCALAPPDATA%/VoxDose; portable data goes alongside the EXE. Open the folder from Settings. Uninstallation preserves data. Export results creates another set with figures and a unique identifier; Save session lets you choose another file.'),
        T('As sessões não contêm áudio bruto, mas incluem medidas e metadados inseridos. Não são criptografadas. Mantenha os áudios e calibrações originais se quiser recalcular resultados. O hash registrado é do PCM do canal escolhido.','Sessions do not contain raw audio, but include features and entered metadata. They are not encrypted. Keep original audio and calibration recordings to recalculate results. The stored hash is for the selected channel PCM.')],
        'table':[[T('Arquivo','File'),T('Conteúdo','Contents')],['session.voxdose',T('Sessão ZIP/JSON/CSV reabrível, sem executar código.','Reopenable ZIP/JSON/CSV session, without executing code.')],['VoxDose_results.xlsx',T('Resumo, janelas, CPPS/HNR, metadados e qualidade.','Summary, windows, CPPS/HNR, metadata and quality.')],['VoxDose_results.png',T('Tabela completa de doses e outras medidas em PNG, com unidades e créditos.','Full PNG table of doses and other measures, with units and credits.')],['frames.csv.gz',T('Todos os quadros, com tempo e duração real.','All frames, with time and actual duration.')],['acoustic_5s.csv / windows.csv',T('Observações acústicas e resumos temporais.','Acoustic observations and temporal summaries.')],['metadata.json',T('Parâmetros, calibração, versões, autoria e rastreabilidade.','Parameters, calibration, versions, authorship and provenance.')],['figures/*.png / *.svg',T('Painel conjunto e gráficos individuais opcionais.','Overview and optional individual figures.')],['diary.csv',T('Avaliações perceptivas, quando presentes na exportação.','Perceptual ratings when present in the export.')]]})
    pages.append({'title':T('13 / Sensores de contato: modo experimental','13 / Contact sensors: experimental mode'),'paragraphs':[
        T('Contato e acelerometria captam vibração, não pressão acústica aérea diretamente. Identifique o dispositivo e documente local, fixação, pressão de contato, ganho e postura. O VoxDose não verifica estabilidade do acoplamento ou remove automaticamente movimento.','Contact microphones and accelerometers capture vibration, not airborne pressure directly. Identify the device and document location, attachment, contact pressure, gain and posture. VoxDose does not verify coupling stability or automatically remove movement.'),
        T('Sem calibração própria: níveis digitais, tempo/ciclos e medidas de periodicidade exploratórias. Para estimar SPL, selecione pelo menos três referências simultâneas, de suave a forte, com amplitude mínima de 10 dB no digital e na referência. Preservar montagem é essencial.','Without a dedicated calibration: digital levels, time/cycles and exploratory periodicity measures. For estimated SPL, select at least three simultaneous soft-to-loud reference levels spanning at least 10 dB in both digital and reference levels. Unchanged setup is essential.'),
        T('O ajuste produz inclinação, intercepto, RMSE e R². São resultados do ajuste nos pontos, não uma validação independente. Referência A só produz estimativa A; Dd/De/Dr requerem referência Z. Mesmo com Z, as doses de contato permanecem experimentais. Diferenças diretas com contato são bloqueadas.','The fit produces slope, intercept, RMSE and R². These describe the fitted points, not independent validation. An A reference only produces an A estimate; Dd/De/Dr require a Z reference. Even with Z, contact-derived doses remain experimental. Direct contact deltas are withheld.'),
        T('O estudo de Castillo-Allendes e colaboradores, incluindo Eric Hunter (2026), apresenta resultados promissores para F0/CPPS em cenário simulado com dois adultos treinados. Não valida o VoxDose, o uso clínico generalizado ou um índice de fadiga. Veja o relatório para a pesquisa completa.','The study by Castillo-Allendes and colleagues, including Eric Hunter (2026), reports promising F0/CPPS results in a simulated setting with two trained adults. It does not validate VoxDose, general clinical use or a fatigue index. See the report for the full research discussion.')],
        'table':[[T('Observação','Observation'),T('Ação','Action')],[T('Montagem/ganho mudou','Setup/gain changed'),T('Recalibre e registre a mudança.','Recalibrate and document the change.')],[T('Calibração falhou','Calibration failed'),T('Corrija os dados; o programa não aplica uma constante arbitrária de SPL.','Correct inputs; the app does not apply an arbitrary SPL constant.')],[T('CPPS/HNR entre sensores','CPPS/HNR across sensors'),T('Não assuma equivalência; preserve tarefa, protocolo e sensor.','Do not assume equivalence; preserve task, protocol and sensor.')]]})
    pages.append({'title':T('14 / Solução de problemas e fontes','14 / Troubleshooting and sources'),'paragraphs':[
        T('Sem fonação detectada: confira canal, limites de F0, ruído e limiar. Doses ausentes: confirme calibração e disponibilidade de SPL Z. Saturação: regrave com ganho menor. Áudio não abre: converta uma cópia para WAV/FLAC sem alterar o original. Cancelamento ocorre entre blocos ou figuras; aguarde o término antes de fechar.','No voicing: check channel, F0 bounds, noise and gate. Missing doses: check calibration and SPL Z availability. Clipping: re-record at lower gain. Audio cannot open: convert a copy to WAV/FLAC, preserving the original. Cancellation occurs between blocks or figures; wait for it to finish before closing.'),
        T('Ctrl+O: adicionar áudio. Ctrl+S: salvar sessão. F1: guia. A revisão 2.0.2 inclui EXE portátil e instalador NSIS com manuais, sem exigir Python ou pasta _internal. A pasta logs registra falhas. A compilação macOS precisa ser executada em um Mac; nenhum binário Mac foi gerado neste Windows. Veja RELEASE_2.0.2.md.','Ctrl+O: add audio. Ctrl+S: save session. F1: guide. Revision 2.0.2 includes a portable EXE and NSIS installer with manuals, without requiring Python or an _internal folder. The logs folder records errors. The macOS builder must run on a Mac; no Mac binary was generated on this Windows host. See RELEASE_2.0.2.md.'),
        '[Titze, Švec & Popolo (2003)](https://pmc.ncbi.nlm.nih.gov/articles/PMC3158591/) - '+T('fundamentação das doses.','dose framework.'),
        '[Bottalico & Nudelman (2023)](https://doi.org/10.1044/2023_JSLHR-23-00060) - '+T('dosímetro DIY.','DIY dosimeter.'),
        '[Hunter et al. (2020)](https://pmc.ncbi.nlm.nih.gov/articles/PMC7210446/) - '+T('demanda, resposta, esforço e fadiga.','demand, response, effort and fatigue.'),
        '[Castillo-Allendes et al. / Hunter (2026)](https://doi.org/10.1007/s00405-025-09970-0) - '+T('sensores de contato, prova de conceito.','contact sensors, proof of concept.'),
        '[Praat: Get CPPS](https://uvafon.hum.uva.nl/praat/manual/PowerCepstrogram__Get_CPPS___.html) - '+T('definição e parâmetros.','definition and parameters.'),
        T('Consulte METHODS.md para equações e diferenças do legado; Relatorio_VoxDose_2.0.pdf para decisões e verificações. Desenvolvimento 2.0: Tiago Lima Bicalho Cruz, UFMG. Adaptação dos códigos originais de Pasquale Bottalico. Não há diagnóstico, previsão de lesão ou limite universal de fadiga nesta versão.','See METHODS.md for equations and legacy differences; Relatorio_VoxDose_2.0.pdf for decisions and checks. Version 2.0 development: Tiago Lima Bicalho Cruz, UFMG. Adapted from original code by Pasquale Bottalico. This version provides no diagnosis, injury prediction or universal fatigue limit.') ]})
    story=[];html_sections=[];width=landscape(A4)[0]-76
    for page in pages:
        title=page['title'];story.append(para('VoxDose 2.0' if page.get('cover') else title,'VCover' if page.get('cover') else 'VHead'))
        html_parts=['<h1>'+html.escape(title)+'</h1>']
        if page.get('cover'):
            story.append(para(title,'VSub'));story.append(image_flow(root/'voxdose'/'assets'/'icon.png',120,120));story.append(Spacer(1,15))
            html_parts.append('<img class="icon" src="images/icon.png" alt="VoxDose"/>')
        for text in page.get('paragraphs',[]):
            story.append(para(text,'VSmall' if page.get('image') else 'VBody'))
            html_parts.append('<p>'+markup(text).replace('<font color="#087F8C">','<code>').replace('</font>','</code>')+'</p>')
        if page.get('image'):
            path=crop_image(page['image']);story.append(image_flow(path,width,340))
            story.append(Spacer(1,5));story.append(para(page['caption'],'VSmall'))
            html_parts.append('<a href="images/'+page['image']+'"><img src="images/'+page['image']+'" alt="'+html.escape(title)+'"/></a><p class="caption">'+html.escape(page['caption'])+'</p>')
        if page.get('table'):
            rows=page['table'];cw=[width*.31,width*.1,width*.59] if len(rows[0])==3 else [width*.31,width*.69]
            story.append(table(rows,cw,compact=True));html_parts.append('<table>'+''.join('<tr>'+''.join('<'+('th' if i==0 else 'td')+'>'+html.escape(str(c))+'</'+('th' if i==0 else 'td')+'>' for c in row)+'</tr>' for i,row in enumerate(rows))+'</table>')
        story.append(PageBreak());html_sections.append('<section>'+''.join(html_parts)+'</section>')
    story.pop()
    doc=SimpleDocTemplate(str(docs/(name+'.pdf')),pagesize=landscape(A4),leftMargin=38,rightMargin=38,topMargin=62,bottomMargin=45,
        title='VoxDose 2.0 - '+T('Manual em português brasileiro','English user manual'),author=AUTHOR)
    doc.build(story,onFirstPage=footer(T('Manual do usuário','User manual')),onLaterPages=footer(T('Manual do usuário','User manual')))
    write_html(docs/(name+'.html'),'VoxDose 2.0 - '+T('Manual em português','English manual'),''.join(html_sections),language)

def write_html(path,title,body,language):
    css='''body{margin:0;background:#edf3f7;color:#20354a;font:16px/1.65 "Segoe UI",Arial,sans-serif}main{max-width:1120px;margin:40px auto}section{background:white;padding:34px 44px;margin:24px 0;border-radius:16px;border:1px solid #dbe5ed}h1{font-size:28px;line-height:1.3;color:#0b3548}h2{color:#087f8c;font-size:22px}h3{font-size:18px}a{color:#087f8c}img{display:block;max-width:100%;height:auto;border-radius:9px;margin:20px auto}.icon{width:140px}.caption{font-size:14px;color:#687f90}table{border-collapse:collapse;width:100%;font-size:14px}td,th{text-align:left;padding:12px;vertical-align:top;border-bottom:1px solid #e0e9ef}th{background:#dfeff0}tr:nth-child(even){background:#f5f8fa}code{color:#087f8c}footer{padding:20px;color:#64788a;font-size:13px}p{overflow-wrap:anywhere}@media print{body{background:white}main{margin:0}section{border:0;break-before:page}a{color:inherit}}'''
    path.write_text('<!doctype html><html lang="'+language.replace('_','-')+'"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+html.escape(title)+'</title><style>'+css+'</style><main>'+body+'<footer>'+html.escape(AUTHOR+' - '+AFFILIATION)+'</footer></main></html>',encoding='utf-8')

def report():
    lines=(docs/'REPORT.md').read_text(encoding='utf-8').splitlines();story=[];parts=[];paragraph=[];tab=[];width=A4[0]-76
    def flush_p():
        if paragraph:
            text=' '.join(paragraph);story.append(para(text));parts.append('<p>'+markup(text)+'</p>');paragraph.clear()
    def flush_t():
        if tab:
            rows=[r for r in tab if not all(re.fullmatch(r'[-: ]+',c) for c in r)]
            story.append(table(rows,[width*.31,width*.69] if len(rows[0])==2 else [width/len(rows[0])]*len(rows[0])))
            parts.append('<table>'+''.join('<tr>'+''.join('<td>'+markup(c)+'</td>' for c in row)+'</tr>' for row in rows)+'</table>');tab.clear();story.append(Spacer(1,10))
    for line in lines+['']:
        if line.startswith('!['):
            flush_p();flush_t();match=re.match(r'!\[([^\]]*)\]\(([^)]+)\)',line)
            if match:
                path=(docs/match.group(2)).resolve();story.append(image_flow(path,width,260));story.append(para(match.group(1),'VSmall'))
                parts.append('<img src="'+html.escape(match.group(2))+'" alt="'+html.escape(match.group(1))+'"/>')
            continue
        if line.startswith('|'):
            flush_p();tab.append([c.strip() for c in line.strip('|').split('|')]);continue
        flush_t()
        if not line.strip():flush_p();continue
        if line.startswith('#'):
            flush_p();level=len(line)-len(line.lstrip('#'));text=line.lstrip('# ').strip()
            story.append(para(text,'VCover' if level==1 else 'VHead' if level==2 else 'VSub'))
            parts.append(f'<h{min(level,3)}>'+html.escape(text)+f'</h{min(level,3)}>')
        elif line.startswith('- '):flush_p();story.append(para('• '+line[2:]));parts.append('<p>• '+markup(line[2:])+'</p>')
        else:paragraph.append(line.strip())
    doc=SimpleDocTemplate(str(docs/'Relatorio_VoxDose_2.0.pdf'),pagesize=A4,leftMargin=38,rightMargin=38,topMargin=62,bottomMargin=45,
        title='VoxDose 2.0 - Relatório de pesquisa e desenvolvimento',author=AUTHOR)
    doc.build(story,onFirstPage=footer('Relatório de desenvolvimento'),onLaterPages=footer('Relatório de desenvolvimento'))
    write_html(docs/'Relatorio_VoxDose_2.0.html','VoxDose 2.0 - Relatório de desenvolvimento','<section>'+''.join(parts)+'</section>','pt_BR')

def render_and_check():
    import pymupdf
    info=[]
    for path in [docs/'Manual_pt_BR.pdf',docs/'Manual_en.pdf',docs/'Relatorio_VoxDose_2.0.pdf']:
        out=qa/path.stem;out.mkdir(exist_ok=True);images_out=[]
        with pymupdf.open(path) as pdf:
            for i,page in enumerate(pdf):
                png=out/f'page_{i+1:02d}.png';page.get_pixmap(matrix=pymupdf.Matrix(1.25,1.25)).save(png);images_out.append(png)
                if not page.get_text().strip():raise ValueError(f'Empty PDF page: {path.name}:{i+1}')
            info.append({'file':path.name,'pages':len(pdf),'bytes':path.stat().st_size})
        thumbs=[]
        for p in images_out:
            im=PILImage.open(p).convert('RGB');im.thumbnail((380,280));tile=PILImage.new('RGB',(400,310),'#e4ebf0');tile.paste(im,((400-im.width)//2,10));
            from PIL import ImageDraw
            ImageDraw.Draw(tile).text((12,290),p.stem,fill='#20354a');thumbs.append(tile)
        sheet=PILImage.new('RGB',(400*3,310*math.ceil(len(thumbs)/3)),'white')
        for i,im in enumerate(thumbs):sheet.paste(im,((i%3)*400,(i//3)*310))
        sheet.save(qa/(path.stem+'_contact.png'))
    (qa/'pdf_validation.json').write_text(json.dumps(info,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(info,ensure_ascii=False,indent=2))

if __name__=='__main__':
    manual('pt_BR');manual('en_US');report();render_and_check()
