# daily_ohaasa 자동 제작·게시

대상 Instagram: **@daily_ohaasa**. 월~금은 ABC 오하아사, 토·일은 TV아사히 고고별점.
공휴일도 요일을 기준으로 선택합니다. 표지 제목은 언제나 `오하아사`입니다.

매일 한국 시간 오전 **07:00**에 실행하고, 원문 지연/일시 오류에 대비해 20분 간격으로
09:40까지 다시 확인합니다. GitHub 예약 실행과 원문 갱신이 늦을 수 있으므로 07:00 정각
게시를 보장하지 않습니다. 컴퓨터가 꺼져 있어도 GitHub 호스팅 러너에서 실행됩니다.

## 현재 상태

2026-11-09: ChatGPT Pro 구독의 API 크레딧을 활성화하고 OpenAI Responses API로 전환했습니다.
모델은 `gpt-6.1-terra`, reasoning `medium`이며 초안 작성 후 원문 전체와 대조해 교정합니다.
`OPENAI_API_KEY`는 Responses 호출만 허용하는 제한 권한·만료 없는 키로 GitHub Secret에 저장했습니다.
추가 결제나 자동 충전은 설정하지 않았습니다. 크레딧 부족·API 오류 시 게시를 중단합니다.

[평일·주말 번역 검증](https://github.com/easyman0/daily-ohaasa/actions/runs/42507117590)을 통과했고,
2026-11-06 ABC 및 2026-11-08 고고 원문의 24개 운세·순위·행운 정보를 사람이 대조했습니다.
각각 카드 5장과 10초 무음 영상도 렌더링해 확인했습니다. 이 과거 자료는 검증용이며 게시하지 않습니다.
실제 예약 게시에는 실행 당일 공식 원문만 사용합니다.

`AUTO_PUBLISH=true`로 매일 07:00 KST 예약 게시를 활성화했습니다. 첫 예약 대상은 2026-11-09입니다.
활성화 시점에는 아직 첫 실제 게시 전입니다. 실행·게시 결과는 Actions 및 `.state/YYYY-MM-DD.json`에서 확인하세요.
[기존 Instagram 미게시 미디어 검사](https://github.com/easyman0/daily-ohaasa/actions/runs/42235058651)도 통과했습니다.

## 생성물

- 1080×1440 JPEG 5장: 전체 순위 표지 + 별자리별 운세 4장.
- 주말 상세 카드: 행운의 색 + 행운 아이템. 원문 ‘행운의 열쇠’는 장소·활동·인물일 수도 있습니다.
- 1080×1920, 10초/30fps 무음 MP4: 검정 베젤, 첫 화면부터 전체 순위, 1위 옆 점만 깜빡임.
- 기존 말투의 카드·릴스 설명문. 출처는 `source.json`에 실제 제공처로 기록합니다.
- Windows에서는 기존 맑은 고딕/Georgia, Linux 클라우드에서는 Noto Sans CJK KR/Liberation Serif.
  레이아웃과 색상은 같지만 폰트 모양·줄 폭은 조금 다릅니다. `FONT_REGULAR`, `FONT_BOLD`,
  `FONT_NUMBER` 경로로 교체할 수 있습니다. 상용 Windows 폰트는 저장소에 포함하지 않았습니다.

## 무료 구성을 위한 준비

1. `easyman0/daily-ohaasa` **공개 저장소**에 이 프로젝트의 파일을 올립니다.
   공개 릴리스의 JPEG/MP4 URL을 Meta가 가져가므로 이 구성은 비공개 저장소를 지원하지 않습니다.
   코드, 완성 이미지·영상, 번역문, 게시 상태는 공개됩니다. 비밀번호/키는 포함하지 않습니다.
2. OpenAI Platform에서 사용 가능한 API 크레딧을 확인하고 Responses API 호출 권한의 키를 준비합니다.
   현재 워크플로는 OpenAI를 사용합니다. 구독 포함 크레딧이 소진되면 추가 결제 없이 실패하도록
   API 결제 수단과 자동 충전을 설정하지 않았습니다.
3. Meta 개발자 앱의 **Instagram API with Unified Login**을 설정하고
   `daily_ohaasa` 크리에이터 계정으로 승인합니다. 게시 권한
   `instagram_basic`, `instagram_content_publish`가 필요합니다.
   개발/테스터 역할 및 앱 검수 요건은 Meta 대시보드에서 해당 계정 조건을 확인합니다.
4. 통합 로그인 구성의 **시스템 사용자 토큰**과 해당 Instagram 숫자 User ID를 준비합니다.
   Instagram 비밀번호, Facebook Page 토큰, 예전 Basic Display 토큰을 넣지 마세요.
5. GitHub 저장소 → Settings → Secrets and variables → Actions에 아래 Secrets를 등록합니다.

| Secret | 값 |
|---|---|
| `OPENAI_API_KEY` | OpenAI Responses 호출 권한의 프로젝트 키 |
| `IG_USER_ID` | Instagram API가 반환한 해당 계정의 숫자 ID |
| `IG_ACCESS_TOKEN` | 통합 로그인 시스템 사용자 토큰 |
| `STATE_ENCRYPTION_KEY` | 기존 Instagram Login 방식에만 필요한 Fernet 키. 통합 로그인에서는 불필요 |

키 생성: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`
키는 채팅·소스·스크린샷에 올리지 말고 GitHub Secret 입력란에 직접 넣으세요.
기존 `.state/auth.json`이 있으면 암호화 키를 임의로 바꾸지 마세요.

## 최초 검증과 활성화

1. Actions → Tests 통과를 확인합니다. `Check translation`은 날짜 입력이 없으면 보관된 평일·주말 원문으로 검증합니다. 날짜를 입력하면 해당 날짜의 공식 원문을 조회하며, 없으면 실패합니다.
2. Actions → Daily ohaasa → Run workflow → **preview**로 실행합니다.
   생성 파일은 실행 화면의 Artifacts에서 받을 수 있습니다. Instagram에는 게시하지 않습니다.
3. 카드·번역·폰트를 확인합니다. 3:4 이미지를 Meta가 거부하는 경우 임의로 자르거나 바꾸지 않고
   실패합니다. 실제 계정의 API 지원 범위를 확인한 뒤에만 크기 정책을 변경하세요.
4. 실제 게시할 준비가 끝나면 Actions **Variables**에 `AUTO_PUBLISH=true`를 설정합니다.
   다음 07:00 예약부터 실행됩니다. 설정 활성화와 첫 실제 게시 성공은 구분해서 확인하세요.
5. 즉시 게시 테스트는 07:00–10:00 KST에 Run workflow의 `publish`로 실행합니다.
   이는 공개 카드 게시물과 릴스를 각각 하나 게시합니다. 별도 가짜 날짜 테스트는 지원하지 않습니다.

워크플로에서 `TRANSLATION_PROVIDER=openai`, `OPENAI_MODEL=gpt-6.1-terra`를 지정합니다. 선택 Variables: `IG_API_VERSION`(기본 `v27.0`), `IG_LOGIN_MODE`(기본 `unified`).
GitHub 기본 `GITHUB_TOKEN`이 저장소 contents 쓰기 권한을 가져야 상태와 미디어를 저장할 수 있습니다.

## 지속 운영

2026-11-07에 `Daily Ohaasa Always On` 구성에서 시스템 사용자 토큰의 만료를 `안 함`으로
설정하고 새 토큰을 `IG_ACCESS_TOKEN`에 저장했습니다. 새 토큰의 계정 연결 검사를
[통과했습니다](https://github.com/easyman0/daily-ohaasa/actions/runs/42239985312).
정기적인 60일 갱신은 필요하지 않습니다. 권한 철회 등으로 토큰이 무효화되면 재연결이
필요합니다. 연결 검사 성공은 실제 게시 성공을 뜻하지 않습니다.
통합 로그인은 graph.facebook.com을 사용합니다.
기존 Instagram Login을 명시적으로 선택한 경우에만 7일마다 갱신하고 암호화한 값을
.state/auth.json에 저장합니다. 액세스 토큰 평문은 저장소나 로그에 쓰지 않습니다.
Meta 권한 철회·비밀번호 변경·만료 등으로 연결이 끊기면 사용자 재인증이 필요합니다.
새 토큰을 `IG_ACCESS_TOKEN`에 등록하면 다음 실행에서 새 연결로 인식합니다.

날짜별 게시 상태는 `.state/YYYY-MM-DD.json`입니다. 카드가 성공하고 릴스가 실패했다면
다음 실행은 릴스만 이어서 처리합니다. 게시 요청 결과가 불명확하면 자동 재게시를 멈추고
해당 컨테이너가 PUBLISHED인지 조회합니다. 상태가 계속 불명확하면 Instagram을 직접 확인한 뒤
복구해야 합니다. `.state`를 삭제하면 중복 게시 방지가 깨질 수 있습니다.

원문 날짜/12개 별자리/순위/행운 정보/번역 길이를 검사합니다. API 장애·할당량 초과·형식 변경 시
다른 날짜나 임의 운세로 대체하지 않습니다. 번역은 생성형 모델이므로 의미 오류 가능성이 남습니다.
Actions 실패 알림은 GitHub 계정의 Notifications 설정에서 받을 수 있습니다.

공개 저장소의 표준 Actions 러너는 무료입니다. 저장 파일의 보관/트래픽 등 플랫폼 한도는 별도입니다.
Artifacts는 3일 보관하고, 게시용 Releases는 이 코드가 자동 삭제하지 않습니다.
장기간 원문이 없으면 GitHub의 공개 저장소 예약 비활성화 정책(60일 무활동)에 유의하세요.

## 로컬 실행

Python 3.12, `pip install -r requirements.txt`.
Ubuntu에서는 `sudo apt-get install fonts-noto-cjk fonts-liberation2`.

```sh
python -m unittest discover -s tests -v
python -m ohaasa.main --mode preview
python -m ohaasa.main --mode preview --source gogo
```

공식 문서: [GitHub 예약 실행](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule),
[GitHub 요금](https://docs.github.com/en/billing/concepts/product-billing/github-actions),
[OpenAI 구독 API 크레딧](https://developers.openai.com/api/docs/guides/chatgpt-api-credits),
[Instagram 게시](https://developers.facebook.com/docs/instagram-platform/instagram-api-with-instagram-login/content-publishing/).
