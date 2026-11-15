# VoxDose 2.0 - revisão corretiva 2.0.1

Códigos originais de dosimetria: **Pasquale Bottalico**. Adaptação e desenvolvimento do VoxDose: **Tiago Lima Bicalho Cruz - UFMG**.

## Correções

- Executável único com Python, Qt/PySide6, bibliotecas de áudio, recursos, manuais e backends de exportação incluídos.
- Retirado o fallback do iniciador para uma instalação externa de Python.
- Corrigida a ausência de matplotlib.backends.backend_svg no empacotamento.
- Paletas explícitas nos temas claro e escuro, eliminando a mistura de cores do tema do Windows.
- Ajuda (i) com texto branco; títulos de grupos, listas, seleção, controles e diálogos com fundos e textos legíveis.
- Ícones dos gráficos redesenhados e contrastantes, inclusive no diário.
- Ajustes de layout dos gráficos efetivos: o modo automático deixa de impedir alterações manuais.
- F0: a média não atravessa pausas; janelas com menos de 0,5 s ou 5% de fonação não geram curva de média. Dados e doses preservados.
- Exportação inclui VoxDose_results.png com todas as doses e demais medidas, unidades, descrições e créditos.
- Retirado o slogan comercial. Os créditos aos códigos originais e à adaptação aparecem juntos no cabeçalho e nas imagens exportadas.

## Três rodadas do mesmo executável

| Rodada | Testes de regressão | Verificações do EXE | Resultado |
|---|---:|---:|---|
| 1 | 49 | 39 | Aprovada |
| 2 | 49 | 39 | Aprovada |
| 3 | 49 | 39 | Aprovada |

Cada rodada copiou somente o EXE para uma pasta isolada, sem _internal e com PATH sem Python. A interface foi exercitada pelo backend nativo do Windows nos dois temas, incluindo ajuda, listas, ajustes e editor completo de curvas, controles do diário e idioma inglês. O caminho real do botão Exportar foi executado e gerou 14 PNGs de gráficos, 14 SVGs, tabela PNG, Excel e sessão reabrível. Os arquivos foram abertos/validados novamente.

O interpretador python311.dll e o backend SVG foram verificados dentro do arquivo empacotado. Isso não é um teste em VM limpa: o computador de desenvolvimento possui Python, mas os testes removem seus caminhos/variáveis e comprovam o uso do runtime extraído do próprio EXE.

Não foi adicionado um VAD treinado nem se afirma remover todo ruído periódico. As limitações de precisão de F0 sob SNR 10 dB documentadas na validação sintética original permanecem; o algoritmo de medição de dose não foi alterado nesta correção visual.

Evidências: validation/corrections/three_runs.json e onefile_round_1, onefile_round_2, onefile_round_3. SHA-256 do EXE: 2ba6c01d78628c629d493c0b3298e9a63243a13852aafb5539d9edd549c63c08
