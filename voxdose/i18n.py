"""Bilingual display labels and field-level explanations."""
METRICS = {
 'duration_s':('Duração da gravação','Recording duration','s','Tempo total representado no arquivo.','Total time represented by the file.'),
 'dt_s':('Dose de tempo · Dt','Time dose · Dt','s','Soma das durações dos quadros classificados como fonados.','Sum of durations of frames classified as voiced.'),
 'dt_pct':('Tempo de fonação','Phonation time','%','100 × Dt / duração total. Não corresponde à inteligibilidade da fala.','100 × Dt / recording duration. This does not measure speech intelligibility.'),
 'dc_cycles':('Dose de ciclos · Dc','Cycle dose · Dc','cycles','Integral de F0 ao longo do tempo fonado.','Integral of F0 over voiced time.'),
 'vli_kcycles':('Índice de carga vocal · VLI','Vocal loading index · VLI','kcycles','Dc dividido por 1000. Unidade: milhares de ciclos, sem divisão por segundo.','Dc divided by 1000. Unit: thousand cycles, not cycles per second.'),
 'dd_m':('Dose de distância · Dd','Distance dose · Dd','m','Estimativa por modelo da distância vibratória acumulada. Requer SPL Z calibrado.','Model estimate of accumulated vibratory distance. Requires calibrated Z-weighted SPL.'),
 'de_j_m3':('Dissipação por volume · De','Dissipation per volume · De','J/m³','Estimativa de energia dissipada por unidade de volume de tecido; não é energia total em joules.','Estimated dissipated energy per unit tissue volume; not total energy in joules.'),
 'dr_j':('Energia radiada · Dr','Radiated energy · Dr','J','Modelo de radiação esférica, calculado com SPL Z e distância em metros.','Spherical radiation model using Z-weighted SPL and distance in metres.'),
 'f0_mean':('F0 média','Mean F0','Hz','Média ponderada pela duração, somente nos quadros fonados.','Duration-weighted mean over voiced frames only.'),
 'f0_sd':('Desvio padrão de F0','F0 standard deviation','Hz','Dispersão de F0 nos quadros fonados. Não inclui zeros artificiais de silêncio.','F0 spread over voiced frames. Artificial silence zeros are excluded.'),
 'f0_p10':('F0 · percentil 10','F0 · 10th percentile','Hz','Percentil ponderado pelo tempo de fonação.','Percentile weighted by phonation time.'),
 'f0_p50':('F0 · mediana','F0 · median','Hz','Mediana ponderada pelo tempo de fonação.','Median weighted by phonation time.'),
 'f0_p90':('F0 · percentil 90','F0 · 90th percentile','Hz','Percentil ponderado pelo tempo de fonação.','Percentile weighted by phonation time.'),
 'f0_range_st':('Amplitude P90-P10 de F0','F0 P90-P10 range','st','12 × log2(P90/P10). Amplitude robusta em semitons.','12 × log2(P90/P10). Robust range in semitones.'),
 'spl_z_mean':('SPL Z médio na fonação','Mean voiced SPL Z','dB SPL','Média aritmética dos níveis não ponderados, na distância indicada. Diferente do Leq.','Arithmetic mean of unweighted levels at the specified distance. Different from Leq.'),
 'spl_z_sd':('Desvio padrão de SPL Z','SPL Z standard deviation','dB','Dispersão do SPL Z nos quadros fonados.','SPL Z spread over voiced frames.'),
 'spl_z_leq':('Leq Z na fonação','Voiced Leq Z','dB SPL','Média energética: 10 log10 da média ponderada de 10^(L/10), apenas na fonação.','Energy mean: 10 log10 of the weighted mean of 10^(L/10), during phonation only.'),
 'spl_a_mean':('SPL A médio na fonação','Mean voiced SPL A','dBA','Média dos níveis com filtro A digital. A calibração não certifica o sistema como sonômetro.','Mean levels after digital A filtering. Calibration does not certify the system as a sound level meter.'),
 'spl_a_leq':('Leq A na fonação','Voiced Leq A','dBA','Média energética A somente durante fonação; não equivale a LAeq ambiental de toda a sessão.','A-weighted energy mean during phonation; not whole-session environmental LAeq.'),
 'level_mean':('Nível médio exibido','Mean displayed level','dB','dBFS sem calibração; SPL A quando disponível; caso contrário SPL Z. Consulte a unidade no gráfico.','dBFS when uncalibrated; SPL A if available, otherwise SPL Z. Check plot units.'),
 'cpps_db':('CPPS · janelas de 5 s','CPPS · 5 s windows','dB','Prominência do pico cepstral suavizado via Praat. Janelas originais de 5 s, sem remover pausas; mínimo 20% de fonação. Dependente do protocolo e sensor.','Smoothed cepstral peak prominence via Praat. Original 5 s windows without pause removal; minimum 20% voicing. Protocol and sensor dependent.'),
 'hnr_db':('HNR · exploratório','HNR · exploratory','dB','Razão harmônico-ruído por autocorrelação. Influenciada pelo ruído, tarefa e sensor; não é medida específica de esforço.','Autocorrelation harmonics-to-noise ratio. Affected by noise, task and sensor; not specific to effort.'),
 'pause_s':('Tempo sem fonação detectada','Time without detected voicing','s','Inclui silêncio, sons não vozeados, ruído e possíveis falhas do detector. Não comprova repouso fisiológico.','Includes silence, unvoiced sounds, noise and detector misses. Does not establish physiological rest.'),
 'pause_count':('Intervalos sem fonação ≥0,25 s','Nonvoicing intervals ≥0.25 s','n','Contagem de segmentos contíguos de pelo menos 250 ms sem fonação detectada.','Count of contiguous segments lasting at least 250 ms without detected voicing.'),
 'long_pause_count':('Intervalos sem fonação ≥5 s','Nonvoicing intervals ≥5 s','n','Intervalos longos no detector. Não devem ser interpretados como recuperação tecidual medida.','Long detector intervals. Do not interpret as measured tissue recovery.'),
 'max_pause_s':('Maior intervalo sem fonação','Longest nonvoicing interval','s','Maior duração contígua sem fonação detectada.','Longest contiguous duration without detected voicing.'),
 'bout_median_s':('Trecho fonado · mediana','Voiced bout · median','s','Duração mediana de segmentos fonados contíguos, sem unir pausas.','Median duration of contiguous voiced segments, without bridging pauses.'),
 'max_bout_s':('Maior trecho fonado','Longest voiced bout','s','Maior segmento contíguo de quadros fonados.','Longest contiguous run of voiced frames.'),
 'clipping_pct':('Amostras próximas da saturação','Samples near clipping','%','Percentual de amostras digitais com magnitude ≥0,999 da escala completa.','Percentage of digital samples with magnitude ≥0.999 full scale.'),
}
for key in ['dc_cycles','dd_m','de_j_m3','dr_j']:
    base=METRICS[key]
    METRICS[key+'_per_hour']=(base[0]+' / hora gravada',base[1]+' / recording hour',base[2]+'/h',
      'Total normalizado por hora de gravação, para comparar durações diferentes.','Total normalized per recording hour, for comparing different durations.')
    METRICS[key+'_per_phonation_s']=(base[0]+' / segundo fonado',base[1]+' / voiced second',base[2]+'/s',
      'Total dividido por Dt. Usar junto ao total, pois descreve intensidade de exposição e não sua duração.','Total divided by Dt. Interpret alongside the total: this describes exposure intensity, not its duration.')

WARNINGS={
 'uncalibrated':('Sem calibração: níveis em dBFS; Dd, De e Dr indisponíveis.','Uncalibrated: levels in dBFS; Dd, De and Dr unavailable.'),
 'contact_experimental':('Sensor de contato: medidas experimentais, sem equivalência clínica estabelecida com microfone aéreo.','Contact sensor: experimental measures; clinical equivalence with an air microphone is not established.'),
 'calibration_residual':('Resíduo de calibração >2 dB: verifique os pontos, ganho e acoplamento.','Calibration residual >2 dB: check points, gain and coupling.'),
 'single_point_calibration':('Calibração de um ponto: linearidade do conjunto não foi verificada.','Single-point calibration: system linearity has not been checked.'),
 'cpps_failed':('CPPS indisponível em uma ou mais janelas; consulte os dados exportados.','CPPS unavailable in one or more windows; check exported data.'),
 'no_voicing':('Nenhuma fonação detectada: confira canal, limiares e faixa de F0.','No voicing detected: check channel, gates and F0 range.'),
 'clipping':('Saturação detectada: a qualidade e a intensidade podem estar distorcidas.','Clipping detected: quality and intensity may be distorted.'),
 'low_sample_rate':('Taxa <16 kHz: medidas espectrais e filtro A têm banda limitada.','Sample rate <16 kHz: spectral measures and A filter have limited bandwidth.'),
}

def metric(key,language='pt_BR'):
    item=METRICS.get(key,(key,key,'','',''))
    return (item[0],item[2],item[3]) if language=='pt_BR' else (item[1],item[2],item[4])

def fmt(value,language='pt_BR',digits=3):
    import math
    if value is None or not math.isfinite(float(value)):return '—'
    val=float(value)
    if val and abs(val)<.001:s=f'{val:.3e}'
    elif abs(val)>=10000:s=f'{val:,.1f}'
    else:s=f'{val:,.{digits}f}'.rstrip('0').rstrip('.')
    return s.translate(str.maketrans({',':'.','.':','})) if language=='pt_BR' else s
