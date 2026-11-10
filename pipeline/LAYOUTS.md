# 포맷별 레이아웃

`layout=` 에 쓸 수 있는 이름. **여기 없는 이름을 쓰면 렌더가 죽는다.**
`--stills` 로 먼저 돌리면 어느 장면이 깨지는지 바로 보인다.

## `shorts`

| layout | 쓰임 |
| --- | --- |
| `dateline` | 큰 날짜 + 장소 |
| `line` | 자막 한 줄 (pre/em/post, sub) |
| `number` | 큰 숫자 + 위아래 라벨 |
| `statement` | 큰 문장 |
| `breath` | 거의 빈 화면, 작은 글자 하나 |
| `endcard` | 마무리 카드 |

## `channel_e`

| layout | 쓰임 |
| --- | --- |
| `brand` | 채널 카드 (열기·닫기) |
| `dateline` | 큰 날짜 + 장소 |
| `chapter` | 장 구분 (하나·둘·셋) |
| `say` | 가운데 정렬 한 문장 |
| `ask` | 질문 던지기 |
| `big` | 큰 숫자 (가운데) |
| `quote` | 인용 한 줄 |
| `breath` | 거의 빈 화면, 작은 글자 하나 |

## `apple_ad`

| layout | 쓰임 |
| --- | --- |
| `word` | 단어 하나 |
| `phrase` | 짧은 구절 |
| `product` | 제품 사진만 |
| `spec` | 숫자 한 줄 |
| `logo` | 마무리 로고 카드 |
| `blackout` | 검은 화면 전환 |

## 공통 키

| 키 | 뜻 |
| --- | --- |
| `narration` | TTS 가 읽을 글. 비우면 음성 없이 화면만 |
| `hold` | 나레이션 뒤 머무는 시간(초). 최소 0.6 |
| `image` | `assets/` 안의 파일명 |
| `image_focus` | 이미지 세로 위치 0(위)~100(아래), 기본 45 |
| `caption` | 아주 작은 각주 (출처) |
| `accent` | `red` / `amber` / `emerald` |
| `cut_music` | 그 장면 동안 배경음을 끊는다 |
| `dry` | 건조한 타격음 한 번 |
| `no_impact` | 숫자 장면이어도 저음 임팩트를 넣지 않는다 |
| `no_mark` | 우하단 채널 마크를 숨긴다 (channel_e) |
