<div align="center">
  <a href="http://bilab.snu.ac.kr/">
    <img src="assets/bilab-logo-light.png" width="760" alt="SNU Biomedical Intelligence Lab" />
  </a>
  <h1>SNU BiLab Skill Set</h1>
  <p><strong>반복되는 연구 작업을 재사용 가능한 실행 체계로.</strong></p>
  <p>
    <img src="https://img.shields.io/badge/SNU-BiLab-0F172A?style=for-the-badge" alt="SNU BiLab" />
    <img src="https://img.shields.io/badge/Skills-3-2457FF?style=for-the-badge" alt="3 skills" />
    <img src="https://img.shields.io/badge/Focus-Research%20Workflow-0F766E?style=for-the-badge" alt="Research Workflow" />
  </p>
  <p>
    <a href="#-skill-catalog">Skill Catalog</a> ·
    <a href="#-quick-start">Quick Start</a> ·
    <a href="#-contributing">Contributing</a> ·
    <a href="http://bilab.snu.ac.kr/">BiLab Website</a>
  </p>
</div>

---

> **스킬은 프롬프트 길이로 완성되지 않습니다.**<br />
> 실행 시점, 품질 기준, 검증 방법까지 갖춰야 실제 작업에 쓸 수 있습니다.

`skillset`은 <strong>SNU BiLab의 연구·개발 워크플로를 위한 스킬 모음집</strong>입니다. 실험 결과 시각화나 논문용 도식 제작처럼 자주 반복되면서도 완성도가 중요한 작업을 모았습니다. 각 스킬에는 에이전트가 따라야 할 절차와 품질 기준이 담겨 있습니다.

## Why this repository exists

연구 자동화는 한 번 결과를 만드는 데서 끝나지 않습니다. **다음 작업에서도 같은 기준으로 결과를 낼 수 있어야 합니다.**

이 저장소는 다음을 목표로 합니다.

- **Repeatable** — 사람과 세션이 바뀌어도 같은 절차를 따릅니다.
- **Verifiable** — 결과물뿐 아니라 검증 방법까지 함께 정의합니다.
- **Editable** — 이후 연구자가 직접 수정하고 확장할 수 있는 산출물을 만듭니다.
- **Research-grade** — 보기 좋은 결과보다 정직하고 재현 가능한 결과를 우선합니다.
- **Composable** — 하나의 거대한 에이전트 대신, 목적이 분명한 작은 스킬을 조합합니다.

## 🧰 Skill Catalog

| Skill | What it does | Best for | Output |
|---|---|---|---|
| [`dashboard`](skills/dashboard) | 실험·평가 결과를 한눈에 보고 샘플 단위까지 탐색할 수 있는 단일 파일 대시보드를 제작합니다. | ML 실험, benchmark, audit, leaderboard, A/B test | Self-contained HTML |
| [`minimal-scientific-svg`](skills/minimal-scientific-svg) | 논문과 발표 자료에 사용할 절제된 과학 도식을 편집 가능한 벡터로 제작하고 PPTX로 변환·검증합니다. | Workflow, architecture, clinical figure, conceptual diagram | Editable SVG / PPTX |
| [`making-conference-posters`](skills/making-conference-posters) | 논문에서 A0 학회 포스터를 제작합니다. 실제 물리 크기로 조판하고 들어맞는지 **측정**한 뒤 인쇄용 PDF·PPTX로 내보냅니다. | Conference poster, A0 print | Print-ready PDF / PPTX |

## 🚀 Quick Start

설치할 스킬 이름과 아래 저장소 주소를 에이전트에게 전달하세요.

[https://github.com/snubilab/skillset](https://github.com/snubilab/skillset)

```text
이 저장소에서 dashboard 스킬을 설치해줘:
https://github.com/snubilab/skillset
```

에이전트가 해당 스킬을 찾아 현재 환경의 skills 디렉터리에 설치합니다.

## Quality Bar

SNU BiLab 스킬에는 프롬프트뿐 아니라 실행 조건과 검증 절차가 함께 들어갑니다.

1. **Trigger가 명확해야 합니다.** 언제 쓰고, 어떤 작업에는 쓰지 않을지 설명합니다.
2. **결과물이 정의되어야 합니다.** 파일 형식과 완료 조건을 구체적으로 적습니다.
3. **실패 조건을 숨기지 않습니다.** 오류를 조용히 넘기는 fallback 대신 실패가 드러나게 합니다.
4. **최소 검증이 포함되어야 합니다.** lint, parser, render, visual QA 중 작업에 필요한 검사를 제공합니다.
5. **재사용 자산을 함께 둡니다.** template과 script는 반복해서 쓸 수 있도록 스킬과 함께 보관합니다.
6. **연구적 정직성을 지킵니다.** 결과를 과장하는 시각화와 근거 없는 완료 선언을 허용하지 않습니다.

## 🤝 Contributing

새 스킬은 `skills/<kebab-case-name>/` 아래에 추가합니다.

제출 전 체크리스트:

- [ ] `SKILL.md` frontmatter에 고유한 `name`과 구체적인 `description`이 있다.
- [ ] 언제 실행할지와 어떤 작업에는 쓰지 않을지가 구분되어 있다.
- [ ] 실행 절차와 반드시 지킬 제약, 완료 기준이 있다.
- [ ] 가능한 범위에서 자동 검증 스크립트나 재현 가능한 검증 명령을 제공한다.
- [ ] 경로와 예시가 새 환경에서도 동작한다.
- [ ] 불필요한 대용량 산출물, 개인정보, credential이 포함되지 않았다.
- [ ] 실제 작업 1건 이상에서 처음부터 끝까지 검증했다.

스킬에서 중요한 것은 “무엇을 할 수 있는가”보다 <strong>“어떤 기준으로 끝났다고 판단할 수 있는가”</strong>를 분명하게 정하는 일입니다.

## Roadmap

- 연구 문헌 탐색과 근거 종합
- 실험 설계·검증·실패 원인 분석
- 재현 가능한 그림·표 생성
- 논문 작성과 rebuttal 준비
- 데이터·모델 감사와 출처 추적

---

<div align="center">
  <strong>SNU BiLab</strong><br />
  Build once. Verify always. Reuse everywhere.
</div>
