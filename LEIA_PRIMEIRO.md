# Amazon Forest Sentinel — entrega única

Este pacote reúne os módulos do projeto em uma única aplicação Python, com interface em inglês. A interface abre no navegador, mas o processamento e o banco ficam no seu computador.

## Abrir no Windows

1. Extraia o ZIP inteiro.
2. Abra a pasta **Amazon_Forest_Sentinel**.
3. Dê dois cliques em **start_windows.bat**. Na primeira execução, aguarde a instalação das dependências.
4. Quando o navegador abrir, clique em **Load demonstration**.
5. Deixe a janela do terminal aberta enquanto usa o sistema.

Se preferir o PyCharm, abra a pasta como projeto, escolha Python 3.11 ou 3.12 de 64 bits e execute no terminal:

```shell
python -m pip install -r requirements.txt
python server.py
```

Acesse http://127.0.0.1:8765 se o navegador não abrir sozinho.

## Roteiro para conferir

- **Forest overview:** carrega os exemplos sintéticos e mostra prioridades.
- **Data & drone imports → Import bundled real INPE sample:** carrega uma amostra real de oito alertas de 2026. Esses dados estão no espaço FIELD, separado do DEMO.
- **Map & study area → Fit evidence:** localiza os polígonos da amostra. Ative a opção OpenStreetMap somente se desejar carregar o mapa-base pela internet.
- **Image comparison → Use synthetic example pair → Analyze:** compara imagens de exemplo. Repita selecionando NDVI para testar imagens com bandas vermelha e infravermelho próximo.
- **AI assistance → Run local anomaly model:** executa IA local sobre as leituras do exemplo.
- **Evidence explorer:** selecione um registro; depois abra **Human review** para registrar sua verificação e anexar arquivos.
- **Reports & audit:** exporta JSON, CSV ou relatório HTML, que pode ser impresso em PDF.

## IA Gemini

A IA local não usa chave. Para a interpretação opcional pelo Gemini, copie `.env.example` para `.env`, preencha sua chave e um modelo disponível na sua conta e reinicie o sistema. Não envie sua chave para outras pessoas.

## Drones e sensores

O pacote contém importação de manifestos e imagens de drones, receptor HTTP autenticado, cliente com fila e reenvio, ponte USB/serial e exemplo de firmware ESP32/DHT22. As instruções estão em **docs/HARDWARE.md**.

A validação física depende de equipamentos reais e continua pendente. O firmware é um exemplo não compilado neste ambiente. A comparação de imagens exige alinhamento e máscaras válidas; ela aponta possíveis mudanças de vegetação, sem comprovar crime ambiental ou desmatamento evitado.

Os testes do software e a consulta real ao INPE estão descritos em **docs/TEST_REPORT.md**. A conferência visual no seu Windows continua necessária: o ambiente de criação bloqueou a abertura do Chromium para inspeção visual.

Não compartilhe a pasta **data**, o arquivo **.env** ou coordenadas sensíveis em um repositório público.

## Aplicar esta correção na pasta já instalada

1. Pare o servidor com Ctrl+C no terminal.
2. Extraia os arquivos deste pacote sobre a mesma pasta do projeto, aceitando substituir os arquivos do programa.
3. Preserve a pasta data e o arquivo .env: eles não são incluídos neste ZIP.
4. Execute novamente python server.py ou start_windows.bat.
5. Atualize o navegador com Ctrl+F5, abra AI assistance e execute o modelo local novamente.

No cenário DEMO original, o resumo esperado é TRAINING 50, EVALUATED 10, ANOMALIES 3 e NOT FLAGGED 7. Os detalhes incluem os sinais originais do Isolation Forest e a referência robusta calculada somente com o treinamento. Esses resultados verificam o cenário sintético, não a precisão em campo.
