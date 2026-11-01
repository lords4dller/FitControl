# FitControl
Aplicação criada para entrega da 2ª Etapa do Projeto Integrador do 4º Semestre da graduação em Tecnologia em Análise e Desenvolvimento de Sistemas do SENAC.

# SENAC - SERVIÇO NACIONAL DE APRENDIZAGEM COMERCIAL
## Curso de Tecnologia em Análise e Desenvolvimento de Sistemas
### Projeto Integrador: Desenvolvimento de Sistemas Orientado a Dispositivos Móveis e Baseados na Web

**EAD - Ensino à Distância | 2026**

---

# FitControl
> **Aplicativo de gestão de treinos físicos para academias, personal trainers e alunos.**

---

## 👥 Integrantes do Grupo

* **Caio Guilherme Pedrosa de Oliveira**
* **Claudinei Pignonato Junior**
* **Jameson Oliveira Costa**
* **Josimar dos Santos Matias**
* **Rodrigo Prado Luis Nunes**

**Orientador / Professor:** Anderson Clayton Garcia Lopes

---

## 📑 Sumário

1. [Resumo](#1-resumo)
2. [Introdução](#2-introdução)
3. [Produto](#3-produto)
   1. [Visão Geral do Produto (Contextualização)](#31-visão-geral-do-produto-contextualização)
   2. [Partes Interessadas (Stakeholders)](#32-partes-interessadas-stakeholders)
   3. [Personas](#33-personas)
   4. [Jornada do Usuário](#34-jornada-do-usuário)
4. [Referências](#4-referências)
5. [Contas de demonstração](#5-contas-de-demonstração)

---

## 1. Resumo

O **FitControl** é uma solução para a gestão de treinos, avaliações físicas e acompanhamento de alunos em academias e atendimentos autônomos. Estruturado como uma aplicação híbrida (Web e Mobile), o sistema elimina o uso de planilhas e papéis, centralizando informações operacionais e administrativas para otimizar a rotina de Personal Trainers, gestores e alunos.

---

## 2. Introdução

O mercado fitness exige eficiência na prestação de serviços e no acompanhamento dos alunos. O FitControl foi idealizado para suprir falhas no controle manual de fichas e avaliações, oferecendo uma plataforma integrada que permite a prescrição de treinos, monitoramento de métricas físicas e acompanhamento da evolução corporal em tempo real.

---

## 3. Produto

### 3.1 Visão Geral do Produto (Contextualização)

* **Problema Identificado:** Personal trainers e academias de pequeno e médio porte utilizam frequentemente planilhas, anotações em papel e aplicativos de mensagens para controlar alunos, avaliações físicas, treinos e pagamentos. Esse processo dificulta a organização das informações, aumenta o risco de perda de dados e reduz a eficiência do acompanhamento da evolução dos alunos.
* **Público-Alvo:** Personal trainers autônomos, academias de pequeno e médio porte e alunos que buscam acompanhar seus treinos e resultados de maneira prática e organizada.
* **Contexto de Uso:** O sistema será utilizado no ambiente das academias e também remotamente por profissionais e alunos. Os personal trainers poderão cadastrar avaliações físicas, montar treinos e acompanhar o desempenho dos alunos. Os alunos poderão acessar seus treinos e consultar seu histórico de evolução via dispositivos móveis.
* **Justificativa da Solução:** O crescimento do mercado fitness aumenta a necessidade de ferramentas que auxiliem no gerenciamento diário. O FitControl surge para centralizar informações importantes em um único ambiente, promovendo organização, produtividade e qualidade no atendimento.
* **Tipo de Solução:** Solução híbrida composta por uma **Plataforma Web** (gestão administrativa e prescrição de treinos) e um **Aplicativo Mobile** (acompanhamento pelos alunos e profissionais).

#### Principais Funcionalidades Previstas
* Cadastro e gerenciamento de alunos;
* Registro de avaliações físicas;
* Criação e atualização de treinos personalizados;
* Controle de frequência dos alunos;
* Agenda de atendimentos;
* Histórico de evolução física com gráficos;
* Emissão de relatórios gerenciais;
* Consulta de treinos via aplicativo;
* Visualização de avaliações físicas e evolução corporal;
* Notificações e lembretes de atividades.

---

### 3.2 Partes Interessadas (Stakeholders)

| Stakeholder | Papel no Projeto / Contexto de Uso | Interesses e Expectativas | Grau de Influência / Impacto |
| :--- | :--- | :--- | :--- |
| **Academias de pequeno e médio porte** | Organizações clientes / Ambiente de implantação | Utilizar o sistema para auxiliar no gerenciamento de alunos, treinos, avaliações físicas, frequência e agenda; melhorar a organização e eficiência. | Alto / Alto |
| **Personal trainers** | Usuários operacionais centrais (Web / Mobile) | Cadastrar e acompanhar alunos, registrar avaliações físicas, elaborar treinos personalizados e acompanhar a evolução dos clientes. | Alto / Alto |
| **Alunos** | Usuários finais (Aplicativo Mobile) | Consultar treinos, visualizar avaliações físicas, acompanhar evolução corporal e receber notificações e lembretes. | Médio / Alto |
| **Administradores das academias** | Usuários administrativos (Plataforma Web) | Operar as funcionalidades administrativas, gerenciar cadastros gerais, acompanhar atividades operacionais e consultar relatórios. | Alto / Alto |
| **Gestores ou proprietários das academias** | Patrocinadores / Tomadores de decisão de negócio | Obter resultados na melhoria da organização, ganho de produtividade, acompanhamento da retenção de alunos e acesso a dados para tomadas de decisão. | Alto / Alto |
| **Equipe de desenvolvimento** | Criadores técnicos da solução | Realizar levantamento de requisitos, arquitetura, desenvolvimento, testes, manutenção e evolução técnica da solução. | Alto / Alto |
| **Equipe de suporte e manutenção** | Suporte operacional e pós-implantação | Auxiliar os usuários na resolução de dúvidas e dificuldades operacionais, garantindo a estabilidade e pleno funcionamento do sistema. | Médio / Médio |

---

### 3.3 Personas

#### Persona 1: Giuseppe Gourlami
* **Idade:** 35 anos
* **Profissão:** Personal Trainer
* **Objetivos:** Dar aulas, preparar e acompanhar os treinos dos alunos nas academias onde atua.
* **Necessidades:** Plataforma para manter o acompanhamento personalizado e organizado dos alunos de acordo com as possibilidades e limitações de cada academia.
* **Dores:** Acompanhar treinos de forma descentralizada e física (papel), sem saber o ganho real do aluno (repetições feitas, massa muscular).
* **Nível Tecnológico:** Intermediário (utiliza smartphone e computador com facilidade).

#### Persona 2: Maria Camole
* **Idade:** 23 anos
* **Profissão:** Estudante
* **Perfil Comportamental:** Executora
* **Objetivos:** Melhorar o condicionamento físico com acompanhamento profissional.
* **Necessidades:** Acompanhar a evolução dos treinos de forma prática.
* **Dores:** Dificuldade em conciliar horários síncronos com o personal na academia.
* **Nível Tecnológico:** Nativa digital.

#### Persona 3: Roberto Mendes
* **Idade:** 45 anos
* **Profissão:** Administrador / Proprietário de Academia
* **Perfil Comportamental:** Empreendedor e analítico
* **Objetivos:** Gerenciar cadastros, acompanhar o fluxo de atividades diárias e consultar relatórios gerenciais para tomada de decisão.
* **Necessidades:** Centralizar informações administrativas e melhorar a eficiência operacional da academia.
* **Dores:** Perda de tempo na gestão de documentos, falta de métricas e dificuldade em gerenciar o acesso de personais terceirizados.
* **Nível Tecnológico:** Intermediário (utiliza o computador diariamente nas rotinas do negócio).

---

### 3.4 Jornada do Usuário

#### 4.1 Persona: Giuseppe Gourlami (Personal Trainer)
**Cenário:** Giuseppe chega à academia para iniciar o atendimento de um novo aluno, registra a avaliação física, monta o treino e acompanha a evolução.

| Etapa | Ação do Usuário (Jornada) | Interface Necessária |
| :--- | :--- | :--- |
| **Acesso ao sistema** | Realiza login na plataforma Web utilizando suas credenciais. | Tela de login |
| **Seleção do aluno** | Localiza e seleciona o aluno na lista sob sua responsabilidade. | Tela de listagem/busca de alunos |
| **Registro da avaliação física** | Insere os dados da avaliação (peso, medidas, % de gordura, etc.). | Formulário de avaliação física |
| **Criação do treino personalizado** | Monta o treino definindo exercícios, séries, repetições e carga. | Tela de criação/edição de treino |

* **Necessidade atendida:** Elimina o controle manual em papel, centralizando avaliação, treino e evolução em um único ambiente.

---

#### 4.2 Persona: Maria Camole (Aluna)
**Cenário:** Maria deseja treinar de forma independente, mesmo sem a presença física do personal na academia.

| Etapa | Ação do Usuário (Jornada) | Interface Necessária |
| :--- | :--- | :--- |
| **Acesso ao aplicativo** | Abre o aplicativo mobile e realiza o login. | Tela de login (mobile) |
| **Consulta do treino do dia** | Acessa a área de treinos e visualiza os exercícios programados. | Tela de listagem de treinos |
| **Execução do treino** | Realiza os exercícios marcando cada um como concluído. | Tela de execução de treino (checklist) |
| **Visualização da evolução** | Consulta o histórico de medidas e avaliações anteriores. | Tela de evolução corporal (gráficos/fotos) |


* **Necessidade atendida:** Autonomia para acompanhar o treino e a evolução sem depender de encontros presenciais constantes com o personal.

---

## 5. Contas de demonstração

Contas criadas pelo comando `flask seed`, apenas para testar a aplicação. Todas usam a mesma senha.

| Perfil | Nome | E-mail | Senha | Observação |
| :--- | :--- | :--- | :--- | :--- |
| Administrador | Roberto Mendes | `admin@fitcontrol.test` | `fitcontrol123` | Cadastra alunos e treinadores |
| Treinador | Giuseppe Gourlami | `giuseppe@fitcontrol.test` | `fitcontrol123` | Treinador de Maria e Pedro |
| Treinador | Ana Ribeiro | `ana@fitcontrol.test` | `fitcontrol123` | Sem alunos |
| Aluno | Maria Camole | `maria@fitcontrol.test` | `fitcontrol123` | Com treinos e avaliações físicas |
| Aluno | Pedro Almeida | `pedro@fitcontrol.test` | `fitcontrol123` | Com treino, sem avaliação física |
| Aluno | Lucas Ferreira | `lucas@fitcontrol.test` | `fitcontrol123` | Sem treinador |
