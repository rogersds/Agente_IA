# Feature Specification: SOC Agent — Triagem, Correlação, Geração de Consultas e Proposta de Contenção

**Feature Branch**: `001-soc-triage-correlacao`  
**Created**: 2026-11-23  
**Status**: Draft  
**Input**: Descrição do usuário: "Domínio SOC/SIEM — triagem de alertas, correlação de incidentes, geração de consultas analíticas e proposta de contenção. Piloto 100% local com integrações por capacidades/adapters (fontes de alertas/telemetria, enriquecimento, inteligência de ameaças, busca analítica, fila de propostas de ação, auditoria e política), acesso a LLM por adapter. O agente descreve o que faz e por quê em linguagem de negócio, respeitando R1–R7 da constituição."

## Clarifications

### Session 2026-11-23

- Q: Quais categorias de fontes de leitura o piloto do soc-agent deve poder consultar para triagem, correlação e geração de propostas de consulta? (FR-001, FR-002, FR-005, FR-006) → A: Todas as categorias declaradas no piloto: alertas/telemetria, enriquecimento contextual, inteligência de ameaças e busca analítica (todas em modo leitura, conforme capacidades disponíveis e autorizadas).
- Q: Como uma proposta (de contenção ou de consulta analítica para execução em produção) deve ser considerada aprovada no piloto do soc-agent? (FR-007, FR-009, R2, R6) → A: Registro explícito vinculado à proposta: a proposta só é considerada aprovada quando houver registro associado com identidade do aprovador humano, escopo/objeto aprovado, decisão e timestamp; sem esse registro, permanece pendente/não aprovada. Rejeições também devem ser registradas explicitamente quando informadas.
- Q: Como as análises do piloto devem ser iniciadas: automaticamente quando novos alertas chegam, apenas por solicitação de um usuário, ou de ambas as formas conforme o tipo de análise? (FR-001, FR-005, FR-006, escopo operacional) → A: Híbrido por tipo: triagem de alertas pode ser iniciada automaticamente quando alertas são recebidos e também sob demanda; correlação e geração de propostas de consulta são iniciadas sob demanda por usuário autorizado.
- Q: Quais categorias de ações de contenção o soc-agent pode incluir em propostas no piloto (sempre sem execução automática, com rollback e aprovação humana explícita)? (FR-007, FR-008, R2, R5) → A: Todas as categorias de domínio aplicáveis: rede (ex.: bloquear origem/destino), host (ex.: isolar), identidade/conta (ex.: desabilitar), processo (ex.: interromper) e credenciais/tokens (ex.: revogar), quando houver evidência suficiente, alvo não ambíguo, plano de rollback e registro explícito de aprovação antes de qualquer execução externa.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Triagem de alerta com classificação explicável (Priority: P1)

Como analista de SOC, quero que o agente analise um alerta recebido e apresente uma
classificação inicial fundamentada, para priorizar a resposta com rapidez e transparência
sem executar ações destrutivas.

**Why this priority**: A triagem é a porta de entrada do fluxo operacional; sem
classificação confiável e explicável, correlação e contenção perdem valor e aumentam risco.

**Independent Test**: Pode ser testado fornecendo um alerta isolado (com e sem contexto
suficiente) e verificando que a saída contém classificação, justificativa, confiança,
fontes com timestamp, comportamento sob insuficiência de dados e hipóteses
(principal/alternativa/falso positivo).

**Acceptance Scenarios**:

1. **Dado** que existe um alerta de segurança com dados de contexto suficientes disponíveis
   nas fontes autorizadas de leitura, **quando** o alerta é submetido para triagem, **o
   agente** produz um resultado observável que inclui: (a) **classificação** do alerta com
   **justificativa** explícita e **nível de confiança** explícito; (b) **fontes consultadas**
   com **timestamp** de cada consulta/consulta registrada; (c) declaração de que os dados
   foram suficientes para a análise realizada; e (d) **hipótese principal** e **pelo menos
   uma hipótese alternativa**, incluindo explicitamente a possibilidade de **falso positivo**
   quando aplicável.
2. **Dado** que existe um alerta com informações incompletas, contraditórias ou
   indisponíveis nas fontes autorizadas, **quando** o alerta é submetido para triagem, **o
   agente** NÃO inventa dados nem força conclusão; em vez disso, produz um resultado que
   inclui: (a) **classificação** marcada como **"indeterminado"** (ou equivalente explícito)
   com **justificativa** e **nível de confiança** explícito; (b) **fontes consultadas** com
   **timestamp** (ou indicação explícita de fonte indisponível com timestamp da tentativa);
   (c) **comportamento declarado quando dados são insuficientes**, explicitando o que se
   sabe, o que falta e a necessidade de escalonamento/revisão humana; e (d) **hipótese
   principal** e **pelo menos uma hipótese alternativa**, incluindo **falso positivo**.
3. **Dado** que o conteúdo do alerta ou de dados correlatos inclui texto que tenta instruir
   o agente a ignorar regras, executar comandos ou alterar seu comportamento, **quando** esse
   conteúdo é processado, **o agente** trata o conteúdo como **dado** (não como instrução),
   produz um resultado que inclui: (a) **classificação** do evento de entrada como potencial
   tentativa de manipulação/IoC com **justificativa** e **nível de confiança** explícito; (b)
   **fontes consultadas** com **timestamp**; (c) **comportamento declarado quando dados são
   insuficientes** para confirmar impacto, se aplicável; e (d) **hipótese principal** (ex.:
   tentativa de injeção de instrução em dado externo) e **alternativa** incluindo **falso
   positivo** (ex.: artefato benigno ou texto legítimo), além de sinalizar o evento para
   revisão humana sem obedecer à instrução embutida.

---

### User Story 2 - Correlação de sinais em incidente (Priority: P2)

Como analista de SOC, quero que o agente correlacione múltiplos alertas e evidências
relacionadas em uma visão de incidente, para entender escopo provável e reduzir esforço
manual de investigação.

**Why this priority**: A correlação agrega valor sobre a triagem individual ao revelar
padrões e relações entre eventos, melhorando a qualidade da decisão.

**Independent Test**: Pode ser testado fornecendo um conjunto de alertas/evidências
relacionados e um conjunto sem relação clara, verificando agrupamento, justificativa,
confiança, fontes com timestamp, tratamento de insuficiência e hipóteses alternativas.

**Acceptance Scenarios**:

1. **Dado** que existem múltiplos alertas e evidências com sinais de relação observáveis nas
   fontes autorizadas, **quando** o analista solicita correlação para um período/escopo
   informado, **o agente** produz uma visão de incidente/correlação que inclui: (a)
   **classificação** do cenário correlacionado com **justificativa** e **nível de confiança**
   explícito; (b) **fontes consultadas** com **timestamp** de cada evidência/fonte usada; (c)
   declaração explícita do comportamento adotado quando parte dos dados estiver ausente (se
   houver lacunas) ou confirmação de suficiência; e (d) **hipótese principal** sobre a relação
   entre os eventos e **pelo menos uma hipótese alternativa**, incluindo **falso positivo**
   (ex.: coincidência temporal sem relação causal).
2. **Dado** que os sinais disponíveis são insuficientes para confirmar relação entre eventos,
   **quando** a correlação é solicitada, **o agente** produz resultado que inclui: (a)
   **classificação** "indeterminado" quanto à correlação com **justificativa** e **nível de
   confiança** explícito; (b) **fontes consultadas** com **timestamp**; (c) **comportamento
   declarado quando dados são insuficientes**, indicando quais evidências adicionais seriam
   necessárias para confirmar ou descartar a correlação; e (d) **hipótese principal** e
   **alternativa** incluindo **falso positivo**, sem concluir relação causal inexistente.

---

### User Story 3 - Geração de consulta analítica como proposta revisável (Priority: P3)

Como analista de SOC, quero que o agente gere consultas analíticas para investigação como
artefatos propostos e revisáveis, para acelerar a busca por evidências sem executar
consultas em produção sem controle humano.

**Why this priority**: Consultas bem delimitadas reduzem tempo de investigação, mas
consultas inadequadas podem gerar custo, ruído ou impacto operacional; por isso devem ser
propostas controladas.

**Independent Test**: Pode ser testado solicitando uma consulta para uma hipótese de
investigação e verificando que o agente entrega uma proposta de consulta (não execução em
produção) com metadados exigidos, fontes, confiança, tratamento de insuficiência e
hipóteses.

**Acceptance Scenarios**:

1. **Dado** que o analista fornece um objetivo de investigação com contexto suficiente,
   **quando** solicita a geração de uma consulta analítica, **o agente** produz uma
   **proposta de consulta** (artefato revisável, não executada em produção) que inclui: (a)
   **classificação** da intenção/adequação da consulta com **justificativa** e **nível de
   confiança** explícito; (b) **fontes consultadas** para embasar a proposta com
   **timestamp**; (c) declaração explícita de **janela temporal proposta**, **escopo das
   fontes/dados a consultar** e **estimativa de impacto/custo** (ou justificativa de
   impossibilidade de estimar com escalonamento para revisão), além de indicação de que a
   execução em produção requer revisão/aprovação humana prévia; e (d) **hipótese principal**
   que a consulta pretende validar e **pelo menos uma hipótese alternativa**, incluindo
   **falso positivo**.
2. **Dado** que o objetivo de investigação é vago ou carece de parâmetros essenciais (ex.:
   período, ativo ou entidade de interesse), **quando** a geração de consulta é solicitada,
   **o agente** NÃO assume parâmetros críticos silenciosamente; produz uma proposta que
   inclui: (a) **classificação** "indeterminado" quanto à completude da consulta com
   **justificativa** e **nível de confiança** explícito; (b) **fontes consultadas** com
   **timestamp**; (c) **comportamento declarado quando dados são insuficientes**, listando
   parâmetros faltantes e apresentando uma proposta parcial/restrita apenas quando seguro e
   claramente marcada para revisão; e (d) **hipótese principal** e **alternativa** incluindo
   **falso positivo**.

---

### User Story 4 - Proposta de contenção com aprovação humana e rollback (Priority: P4)

Como respondedor de incidentes, quero receber propostas de contenção fundamentadas, com
plano de reversão e necessidade explícita de aprovação humana, para tomar decisões seguras
sem risco de execução automática.

**Why this priority**: A contenção pode reduzir dano, mas ações erradas ou automáticas podem
ampliar impacto; propostas controladas preservam segurança e governança.

**Independent Test**: Pode ser testado a partir de um incidente classificado com evidências
suficientes e outro com alvo ambíguo, verificando que o agente apenas propõe ações,
exige aprovação humana identificada, declara rollback e trata ambiguidades/insuficiência.

**Acceptance Scenarios**:

1. **Dado** um incidente com evidências suficientes e alvo claramente identificado nas fontes
   autorizadas, **quando** o agente avalia opções de contenção, **o agente** produz
   **apenas uma proposta** (nunca execução) que inclui: (a) **classificação** da ação
   proposta com **justificativa** e **nível de confiança** explícito; (b) **fontes
   consultadas** com **timestamp**; (c) **plano de rollback declarado antes de qualquer
   aprovação**, com pré-condições, passos de reversão, responsáveis/atores necessários,
   validação pós-reversão e limitações; exigência explícita de **aprovação humana
   identificada** (ausência de resposta não é aprovação); e (d) **hipótese principal** que
   motiva a contenção e **pelo menos uma hipótese alternativa**, incluindo **falso
   positivo**.
2. **Dado** um cenário em que o alvo da contenção é ambíguo, o impacto é incerto ou os
   dados são insuficientes para recomendar contenção segura, **quando** a contenção é
   avaliada, **o agente** NÃO propõe execução nem inferir contenção; produz resultado que
   inclui: (a) **classificação** "indeterminado" com **justificativa** e **nível de
   confiança** explícito; (b) **fontes consultadas** com **timestamp**; (c) **comportamento
   declarado quando dados são insuficientes**, bloqueando a proposta de contenção,
   escalando para revisão humana e explicitando o que falta para uma proposta segura; e (d)
   **hipótese principal** e **alternativa** incluindo **falso positivo**.
3. **Dado** que uma ação proposta foi elaborada, **quando** não há registro explícito de
   aprovação humana identificada vinculado à proposta (com identidade do aprovador, escopo/
   objeto, decisão e timestamp), **o agente** mantém o estado como proposta pendente/não
   aprovada e não executada, registrando essa condição de forma observável; o resultado
   inclui: (a) **classificação** do estado da proposta com **justificativa** e **nível de
   confiança** explícito; (b) **fontes consultadas**/registros de decisão com **timestamp**
   (ou indicação explícita de ausência de registro de aprovação); (c) **comportamento
   declarado** de que ausência de resposta ou confirmação não registrada não autoriza
   execução; e (d) **hipótese principal** e **alternativa** relevantes ao risco de executar
   ou não executar, incluindo **falso positivo** do incidente quando aplicável.

---

### Edge Cases

- **Injeção de instrução em dado externo:** conteúdo de alerta/log/intel contém comandos ou
  tentativas de alterar regras; o agente deve tratar como dado, sinalizar como potencial IoC
  e não obedecer (R1).
- **Fontes indisponíveis ou parciais:** timeout, indisponibilidade ou lacunas de cobertura;
  o agente deve declarar insuficiência, registrar tentativas/fontes com timestamp e escalar
  quando necessário (R4, R6).
- **Evidências contraditórias:** sinais conflitantes entre fontes; o agente deve refletir
  conflito na justificativa/confiança e manter hipóteses alternativas/falso positivo.
- **Alvo ambíguo para contenção:** múltiplos ativos/identidades possíveis; o agente deve
  bloquear proposta e escalar (R2, R4).
- **Solicitação implícita de execução destrutiva:** pedido para "bloquear/isolar/revogar"
  imediatamente; o agente deve responder apenas com proposta condicionada a aprovação humana
  e rollback (R2, R5).
- **Parâmetros de consulta ausentes:** período/escopo não informado; o agente não deve
  assumir silenciosamente parâmetros críticos e deve declarar insuficiência (R4, R7).
- **Dados sensíveis em evidências:** presença potencial de segredos/credenciais em entradas;
  o agente não deve propagar segredos em saídas desnecessárias e deve manter tratamento
  read-only e seguro (R3).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001 (Triagem):** O sistema DEVE analisar alertas de segurança provenientes das
  categorias de fontes de leitura autorizadas no escopo do piloto (alertas/telemetria,
  enriquecimento contextual, inteligência de ameaças e busca analítica, conforme
  disponibilidade e autorização) e produzir triagem com classificação, justificativa
  explícita e nível de confiança explícito. A triagem DEVE poder ser iniciada
  automaticamente na chegada/ingestão de alertas e também sob demanda por usuário
  autorizado.
- **FR-002 (Fontes e tempo):** Para cada análise/resultado, o sistema DEVE registrar e
  apresentar as fontes consultadas com timestamp (ou indicação explícita de indisponibilidade
  com timestamp da tentativa).
- **FR-003 (Insuficiência de dados):** Quando os dados forem insuficientes, contraditórios
  ou indisponíveis, o sistema DEVE declarar o comportamento adotado, marcar o resultado como
  "indeterminado" quando apropriado, explicitar o que se sabe e o que falta, e escalar para
  revisão humana conforme necessário (sem inventar dados ou inferir contenção).
- **FR-004 (Hipóteses):** Cada resultado analítico relevante DEVE apresentar hipótese
  principal e pelo menos uma hipótese alternativa, incluindo a possibilidade de falso
  positivo quando aplicável.
- **FR-005 (Correlação):** O sistema DEVE correlacionar múltiplos alertas/evidências
  dentro de um escopo solicitado e apresentar relações prováveis, incertezas e alternativas
  de interpretação. A correlação DEVE ser iniciada sob demanda por usuário autorizado.
- **FR-006 (Geração de consultas):** O sistema DEVE gerar consultas analíticas como
  **propostas** de artefatos revisáveis (não executadas em produção automaticamente),
  declarando janela temporal proposta, escopo das fontes/dados e estimativa de
  impacto/custo (ou justificativa de impossibilidade com escalonamento). A geração de
  propostas de consulta DEVE ser iniciada sob demanda por usuário autorizado.
- **FR-007 (Proposta de contenção):** O sistema DEVE propor ações de contenção apenas como
  recomendações sujeitas a aprovação humana identificada; o sistema NÃO DEVE executar ações
  destrutivas. No escopo do piloto, as propostas podem abranger categorias de domínio
  aplicáveis (rede, host, identidade/conta, processo e credenciais/tokens), somente quando
  houver evidência suficiente, alvo não ambíguo, plano de rollback completo e registro
  explícito de aprovação antes de qualquer execução externa autorizada.
- **FR-008 (Rollback):** Toda proposta de ação/contenção DEVE incluir plano de rollback
  documentado antes de qualquer aprovação, descrevendo pré-condições, passos de reversão,
  responsáveis/atores necessários, validação pós-reversão e limitações.
- **FR-009 (Aprovação humana):** O sistema DEVE exigir aprovação humana identificada para
  execução de ações propostas. Uma proposta só DEVE ser considerada aprovada quando existir
  registro explícito vinculado à proposta contendo identidade do aprovador humano, escopo/
  objeto aprovado, decisão e timestamp; sem esse registro, a proposta permanece pendente/não
  aprovada. Rejeições informadas DEVEM ser registradas explicitamente quando aplicável.
  Ausência de resposta NÃO DEVE ser interpretada como aprovação. Alvos ambíguos DEVEM
  bloquear a proposta e gerar escalonamento.
- **FR-010 (Dado externo como dado — R1):** O sistema DEVE tratar todo conteúdo externo
  (alertas, logs, e-mails, tickets, intel, páginas, descrições) como dado; instruções
  embutidas DEVEM ser tratadas como potenciais IoCs, sinalizadas ao usuário e registradas,
  sem obediência.
- **FR-011 (Read-only por padrão — R3):** O sistema DEVE operar com acesso de leitura por
  padrão nas integrações e NÃO DEVE expor ou persistir credenciais/tokens/chaves/segredos
  em saídas, artefatos versionados ou registros indevidos.
- **FR-012 (Rastreabilidade — R6):** O sistema DEVE produzir registros de auditoria para
  decisões relevantes contendo, no mínimo: entrada, fontes consultadas, raciocínio resumido,
  nível de confiança, versão do modelo, versão do prompt/instruções aplicáveis e desfecho,
  com timestamps/identificadores para correlação. Registros NÃO DEVEM ser editáveis pelo
  agente (apenas apêndices novos).
- **FR-013 (Escalonamento):** O sistema DEVE escalar para revisão humana quando houver
  indeterminação relevante, ambiguidade de alvo, insuficiência de dados críticos, tentativa
  de manipulação/injeção detectada ou impossibilidade de estimar impacto de consulta.

### Key Entities *(include if feature involves data)*

- **Alerta:** evento ou sinal de segurança recebido para análise, com atributos de origem,
  tempo, severidade reportada (se houver) e conteúdo associado tratado como dado.
- **Evidência/Fonte Consultada:** informação obtida de fontes autorizadas de leitura para
  suportar análise, sempre associada a timestamp e identificação da fonte.
- **Incidente/Correlação:** agrupamento lógico de alertas e evidências relacionados (ou
  potencialmente relacionados), com escopo, período e estado de confiança.
- **Consulta Analítica Proposta:** artefato de investigação versionável que descreve
  intenção, janela temporal, escopo de fontes/dados, estimativa de impacto/custo e estado de
  revisão/aprovação para execução.
- **Proposta de Contenção:** recomendação de ação de resposta (não executada) com alvo,
  justificativa, confiança, hipóteses, pré-condições, plano de rollback e estado de
  aprovação humana identificada.
- **Registro de Auditoria:** entrada imutável (append-only do ponto de vista do agente) que
  documenta decisões, fontes, raciocínio, confiança, versões e desfecho.
- **Aprovação Humana:** decisão registrada de um aprovador humano identificado autorizando ou
  rejeitando uma proposta específica, com escopo e timestamp.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001:** 100% das triagens, correlações, propostas de consulta e propostas de contenção
  entregues pelo sistema incluem classificação, justificativa, nível de confiança explícito,
  fontes consultadas com timestamp (ou indisponibilidade justificada com timestamp),
  comportamento declarado em caso de dados insuficientes e hipótese principal com ao menos
  uma alternativa incluindo falso positivo quando aplicável.
- **SC-002:** 100% das ações destrutivas potenciais são apresentadas apenas como propostas;
  0 execuções destrutivas ocorrem sem aprovação humana identificada registrada.
- **SC-003:** 100% das propostas de contenção incluem plano de rollback completo antes de
  qualquer solicitação de aprovação; propostas sem rollback são tratadas como inválidas/não
  emitidas.
- **SC-004:** 100% das consultas analíticas geradas são entregues como artefatos propostos
  com janela temporal, escopo de fontes/dados e estimativa de impacto/custo (ou justificativa
  explícita de impossibilidade) e indicação de necessidade de revisão humana antes de
  execução em produção.
- **SC-005:** 100% dos casos com alvo ambíguo, dados críticos insuficientes ou incerteza
  material relevante resultam em classificação "indeterminado" e escalonamento explícito, sem
  contenção inferida.
- **SC-006:** 100% das tentativas de instrução embutida em dados externos são tratadas como
  dados/potenciais IoCs, sinalizadas e não obedecidas, com registro de auditoria associado.
- **SC-007:** Em avaliações de qualidade do piloto, pelo menos 90% das análises revisadas por
  humanos são consideradas rastreáveis e compreensíveis (fontes, raciocínio e confiança
  suficientes para revisão), sem exposição de segredos em artefatos ou saídas.

## Assumptions

- O piloto opera em ambiente local com acesso de leitura às categorias de fontes declaradas e
  disponíveis para o SOC (alertas/telemetria, enriquecimento contextual, inteligência de
  ameaças e busca analítica), conforme capacidades autorizadas; integrações específicas serão
  tratadas como capacidades/adapters definidos em etapas posteriores, sem presumir produtos
  não declarados.
- Existe um mecanismo organizacional para designar e registrar aprovadores humanos
  identificados e autorizados; os critérios detalhados de autorização serão definidos no
  plano/processo operacional.
- "Timestamp" das fontes consultadas refere-se ao horário de consulta/coleta registrado pelo
  sistema e, quando disponível, ao horário do evento na fonte; indisponibilidades serão
  explicitadas.
- Estimativas de impacto/custo de consultas podem ser aproximadas no piloto quando métricas
  exatas não estiverem disponíveis, desde que a limitação seja declarada e a consulta seja
  submetida a revisão humana.
- A retenção, armazenamento e proteção dos registros de auditoria seguem políticas do
  ambiente piloto; detalhes de implementação e conformidade específica serão definidos em
  etapas técnicas posteriores sem enfraquecer R6.
- O escopo inicial prioriza triagem, correlação, geração de propostas de consulta e propostas
  de contenção; execução automatizada de contenções e integrações de escrita permanecem fora
  de escopo salvo exceções explicitamente declaradas, justificadas e revisadas.
