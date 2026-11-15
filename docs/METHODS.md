# VoxDose 2.0 - métodos e diferenças numéricas

Tiago Lima Bicalho Cruz · Universidade Federal de Minas Gerais (UFMG). 15/11/2026.

Adaptação das rotinas de dose de Pasquale Bottalico, conferida com as equações 14-24 de Titze, Švec e Popolo (2003), presentes no PDF fornecido na pasta Papers. A interface e a implementação 2.0 são desenvolvimento de Tiago Lima Bicalho Cruz. A implementação não foi validada clinicamente nesta entrega.

## 1. Áudio, tempo e seleção de fonação

Leitura por SoundFile em blocos de 30 s, mantendo somente o canal escolhido. Não se usa média estéreo nem seleção automática do canal mais intenso. Arquivos WAV e FLAC são preferenciais; MP3 depende da versão local de libsndfile. A menor taxa aceita é 8 kHz. Taxas abaixo de 16 kHz recebem uma observação de banda limitada.

O tempo de cada quadro é o limite inicial em segundos; `center_s` é seu centro; `dt_s` é a duração real. Limites de quadros de 50 ms são arredondados na grade de amostras para evitar deriva, inclusive em 11025 Hz. O último quadro parcial é preservado.

F0 por autocorrelação Praat, passo de 50 ms e limiar de vozeamento 0,45. Cada bloco recebe contexto bilateral de pelo menos 150 ms (ou 3/F0min, se maior). O pareamento usa os tempos reais do Praat, sem interpolar através de pausas ou extrapolar além de meio passo. Fonação exige F0 válida, nível acima do limiar selecionado e pelo menos uma amostra não nula no quadro original, para rejeitar caudas do filtro em silêncio digital verdadeiro. Esta detecção não identifica o falante nem elimina artefatos de movimento.

## 2. Nível digital, ponderação e calibração

Nível RMS digital = 20 log10(RMS), com escala completa digital = 1. A convenção deve ser mantida em todas as comparações; uma senoide de pico 1 tem RMS -3,01 dBFS. Sem calibração não há SPL físico.

Microfone aéreo: um a três pontos, com mesmo canal/ganho da gravação monitorada. Para cada ponto, mede-se RMS em todo o trecho de calibração, filtrado em A quando a leitura de referência é dBA, ou não ponderado quando dBZ. `offset = média(Lreferência - Ldigital)`; a inclinação é 1. O resíduo é calculado nos pontos; um ponto não verifica linearidade. Silêncio, trechos <0,2 s e saturação >0,1% na calibração geram erro, em vez de usar silenciosamente uma constante arbitrária.

O filtro A é um IIR em seções de segunda ordem, obtido por transformação bilinear dos polos/zeros nominais e normalizado em 1 kHz. Há deformação de frequência perto de Nyquist; o sistema não é um sonômetro certificado. O filtro mantém estado entre blocos. São exportadas trilhas A e Z separadas. Uma calibração escalar pressupõe resposta e ganho suficientemente estáveis; não corrige a resposta em frequência do microfone.

Para o campo livre: `L(r2) = L(r1) + 20 log10(r1/r2)`. Exemplo: 80 dB a 30 cm tornam-se 75,563 dB a 50 cm. Aumentar a distância reduz o nível. A distância é boca-sonômetro de referência, inclusive em contato; não se aplica uma lei de propagação na pele.

Contato/acelerometria: regressão exploratória `Lreferência = a × Ldigital + b` de ao menos três níveis, com amplitude de 10 dB tanto no sinal digital quanto na referência. Guardam-se coeficientes, RMSE, R², canal e arquivos. Esses resíduos são de ajuste, não incerteza de medição ou validação fora da amostra. Calibração A de contato produz somente estimativa A: não permite recuperar SPL Z. Dd/De/Dr ficam indisponíveis nesse caso. Referência Z permite estimativas modeladas experimentais, sujeitas ao acoplamento e às limitações do sensor.

## 3. Equações de dose

Para quadros fonados, `Dt = Σ dt`; `Dc = Σ F0 × dt`; `VLI = Dc/1000`. Percentual de fonação = `100 × Dt / Σ dt`. O denominador inclui o quadro final, permitindo 100% sem ultrapassá-lo por exclusão de meio quadro.

O modelo usa SPL Z referido internamente a 0,5 m:

- `Pth = 0,14 + 0,06 × (F0/Fnom)²` em kPa.
- `Pl - Pth = 10^((SPL50 - 78,5)/27,3)` em kPa.
- `A = 0,05 × L0 × sqrt((Pl-Pth)/Pth)` em m.
- `T = T0/(1 + b × sqrt(F0/Fnom))` em m.
- `eta = k/F0` em Pa.s; `omega = 2πF0`.
- `Dd = Σ 4 × A × F0 × dt` em m.
- `De = Σ 0,5 × eta × (A/T)² × omega² × dt` em J/m³.
- `Dr = Σ 4π × (0,5 m)² × 10^((SPL50-120)/10) × dt` em J.

Constantes históricas: masculino `(Fnom,L0,T0,b,k)=(120;0,016;0,0158;2,15;5,4)`; feminino `(190;0,010;0,01063;1,69;1,4)`. A opção média calcula cada ramo separadamente e tira a média das doses Dd e De. Esses pressupostos anatômicos não representam uma classificação automática de identidade, idade ou fisiologia individual.

O fator 0,05 em A é um coeficiente empírico da equação 14, independente do passo de integração. Não se confunde com os 50 ms dos quadros. Não há multiplicador arbitrário 1000 em Dr nem conversão de De para joules totais sem volume tecidual. As unidades SI e as hipóteses são explícitas.

## 4. Resumos, CPPS e HNR

Médias, desvios padrão populacionais e percentis são ponderados pelo tempo fonado. O desvio padrão não é calculado após multiplicar os níveis por dt, nem inclui zeros de silêncio. Leq de fonação é a média energética somente dos quadros fonados, diferente da média aritmética e do LAeq ambiental de toda a sessão.

CPPS e HNR têm uma observação por janela original de 5 s (última janela parcial se ≥0,2 s), exigindo pelo menos 20% de fonação detectada. Não se removem/concatenam pausas; não se repetem valores como se houvesse novas observações a 20 Hz. Janelas sem critério são NaN, não zero.

CPPS Praat/Parselmouth: PowerCepstrogram com piso 60 Hz, passo 0,002 s, frequência máxima min(5000 Hz, Nyquist), pré-ênfase 50 Hz; Get CPPS sem subtrair tendência antes da suavização, janela temporal 0,01 s, janela de quefrência 0,001 s, faixa de busca igual à F0 configurada, tolerância 0,05, interpolação parabólica, linha de tendência 0,001 s até fim, tipo Straight, ajuste Robust. As versões do Parselmouth e do Praat incorporado são registradas: o protocolo depende delas.

HNR exploratório por `Sound.to_harmonicity_ac`, passo de 10 ms e piso igual ao F0 mínimo. Valores especiais de silêncio do Praat são excluídos. Para resumos de CPPS/HNR, pondera-se a duração da janela pela fração fonada. Um intervalo solicitado dentro de uma janela de 5 s reutiliza a observação dessa janela, com peso proporcional à sobreposição; não gera uma análise acústica subjanela nova.

## 5. Gravações longas e comparações

Não se carrega a forma de onda inteira. Características por quadro permanecem em memória e crescem com a duração; não há promessa de memória estritamente constante. O teste de duas horas inclui F0 e não inclui CPPS. O teste com o áudio original inclui CPPS/HNR.

Resumos temporais não sobrepostos usam a duração real do trecho; taxas por hora usam o tempo gravado e taxas por segundo fonado usam Dt. Totais de durações distintas não equivalem a diferenças de intensidade de exposição. O eixo relativo apenas reescala 0-100% da duração; não sincroniza eventos nem participantes.

Diferenças diretas são disponibilizadas somente com participante, tarefa e dispositivo preenchidos e iguais, além de sensor, canal, modelo, limites F0, limiares, opção CPPS, ponderação, referência de distância e versão do método compatíveis. Contato recebe bloqueio de diferenças diretas por padrão. Isso é uma verificação de metadados, não demonstração de equivalência de tarefas ou ausência de confundidores. Δ é diferença absoluta na unidade da linha; em percentuais é diferença em pontos percentuais, sem teste estatístico.

## 6. Diferenças em relação aos arquivos antigos

- Os fontes principais encontrados já utilizavam PySide6; não foi encontrada implementação Tkinter nos fontes/arquivos ZIP examinados. A versão Tkinter mencionada pode ser um ancestral externo, mas não foi localizada no material fornecido.
- `stima_livello.py` rotulava um estimador FFT não ponderado como dBA. O cálculo dependia da amostragem/janela; calibração e monitoramento usavam tamanhos diferentes. Substituído por RMS, filtragem A real e trilha Z explícita.
- O sinal da correção de distância fazia o nível aumentar ao aumentar a distância. Corrigido.
- As séries eram truncadas ao menor comprimento, sem pareamento por tempos. Substituído por quadros alinhados por seus centros e durações reais.
- No DOSI.m fornecido havia o coeficiente empírico 0,05 em A e um passo 0,05 adicional na integração de Dd; a adaptação Python confundia o primeiro com dt. A nova rotina separa ambos explicitamente e é testada contra troca do passo.
- `Pl-Pth` com constante 72,48 (78,5 - 6,02) pressupunha uma conversão fixa; agora utiliza-se SPL50 e a constante 78,5 da referência.
- De era apresentada como J; a referência fornece energia por volume. Dr usava um fator 1000 e raio fixo de 1 m sem consistência com a referência exibida. Corrigidos e documentados.
- A versão antiga podia produzir medidas físicas sem calibração, com C=50. A versão 2.0 não faz isso.
- CPPS incluía falhas convertidas em zero, pausas removidas e valores repetidos por quadro. A versão 2.0 conserva janelas independentes e indisponibilidade explícita.

Essas mudanças impedem equivalência numérica automática com planilhas antigas. Para comparação longitudinal, reanalise os áudios originais com a mesma versão e o mesmo protocolo.

## 7. Dados e rastreabilidade

Cada sessão contém a configuração, pontos/coeficientes de calibração, seleção de canal, versões, SHA-256 do PCM do canal escolhido, duração e número de amostras. Não é o hash do arquivo original codificado. O formato .voxdose é ZIP com JSON e CSV, sem pickle e sem executar código ao abrir. Não contém a forma de onda, mas contém informações acústicas e os metadados que você inserir. Não é criptografado.

O diário utiliza avaliações numéricas descritivas 0-10 criadas para registro neste programa; não é uma adaptação validada do VFI ou uma escala Borg. Não há score automático de fadiga, risco fonotraumático ou recuperação tecidual.

## Fontes primárias

- Titze IR, Švec JG, Popolo PS. 2003. https://pmc.ncbi.nlm.nih.gov/articles/PMC3158591/
- Bottalico P, Nudelman CJ. 2023. https://doi.org/10.1044/2023_JSLHR-23-00060
- Hunter et al. 2020. https://pmc.ncbi.nlm.nih.gov/articles/PMC7210446/
- Praat, Get CPPS. https://uvafon.hum.uva.nl/praat/manual/PowerCepstrogram__Get_CPPS___.html
- Castillo-Allendes et al. / Hunter. 2026. https://doi.org/10.1007/s00405-025-09970-0
