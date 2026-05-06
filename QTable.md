# Q-Table State And Action Reference

이 문서는 현재 `models/policies.py` 기준으로 `TabularQPolicy`가 사용하는 상태 키 구성 요소와 행동 값을 정리한 것입니다.

## State Key

상태 키는 `ObservationEncoder.encode()`에서 아래 순서의 문자열로 만들어집니다.

형식:

```text
distanceBin|enemyAngleBin|selfHpBin|enemyHpBin|selfStateBin|enemyStateBin|selfCombatReadinessBin|enemyCombatReadinessBin|coverDistanceBin|coverAdvantageBin|itemRaceBin|itemDistanceBin|bulletThreatBin|bulletAngleBin|buffStateBin
```

총 15개 슬롯으로 구성됩니다.

### 1. `distanceBin`
- 원본 값: `distance_to_enemy`
- bin 수: `6`
- 의미: 나와 적의 거리
- 범위:
  - `0`: 매우 가까움
  - `5`: 매우 멈

### 2. `enemyAngleBin`
- 원본 값: `enemy_direction`
- bin 수: `8`
- 의미: 적이 나를 기준으로 어느 방향에 있는지

### 3. `selfHpBin`
- 원본 값: `self_hp / self_hp_max`
- bin 수: `4`
- 의미: 내 체력 비율

### 4. `enemyHpBin`
- 원본 값: `enemy_hp / enemy_hp_max`
- bin 수: `4`
- 의미: 적 체력 비율

### 5. `selfStateBin`
- 원본 값: `state`
- 매핑:
  - `0`: `idle`
  - `1`: `move`
  - `2`: `dash`
  - `3`: `attack`

### 6. `enemyStateBin`
- 원본 값: `enemy_state`
- 매핑:
  - `0`: `idle`
  - `1`: `move`
  - `2`: `dash`
  - `3`: `attack`

### 7. `selfCombatReadinessBin`
- 원본 값:
  - `self_attack_cooldown_ratio`
  - `self_dash_cooldown_ratio`
- bin 수: `3`
- 의미: 내 공격/대시 준비도 평균
- 값이 클수록 즉시 행동 가능한 상태에 가까움

### 8. `enemyCombatReadinessBin`
- 원본 값:
  - `enemy_attack_cooldown_ratio`
  - `enemy_dash_cooldown_ratio`
- bin 수: `3`
- 의미: 적의 공격/대시 준비도 평균

### 9. `coverDistanceBin`
- 원본 값: `nearest_cover_distance`
- bin 수: `6`
- 의미: 가장 가까운 엄폐물까지의 거리

### 10. `coverAdvantageBin`
- 원본 값:
  - `self_position`
  - `enemy_position`
  - `cover_positions`
- 값:
  - `0`: 전술적 엄폐 이점 거의 없음
  - `1`: 약한 엄폐 이점
  - `2`: 의미 있는 엄폐 이점
  - `3`: 매우 좋은 엄폐 이점
- 의미: 엄폐물이 실제로 나와 적 사이를 가로막는지, 내가 더 유리하게 쓸 수 있는지 요약한 값

### 11. `itemRaceBin`
- 원본 값:
  - `item_active`
  - `self_item_distance`
  - `enemy_item_distance`
- 값:
  - `0`: 아이템이 없거나, 아이템 경쟁에서 유리하지 않음
  - `1`: 서로 비슷함
  - `2`: 내가 아이템에 더 유리하게 가까움

### 12. `itemDistanceBin`
- 원본 값: `self_item_distance`
- bin 수: `6`
- 의미: 아이템까지의 거리

### 13. `bulletThreatBin`
- 원본 값:
  - `enemy_bullet_count`
  - `nearest_enemy_bullet_distance`
  - `second_enemy_bullet_distance`
- 값:
  - `0`: 적 총알 위협 없음
  - `1`: 멀리 있는 총알 위협
  - `2`: 중간 거리 총알 위협
  - `3`: 가까운 총알 1발 위협
  - `4`: 가까운 총알 2발 이상 위협

### 14. `bulletAngleBin`
- 원본 값: `nearest_enemy_bullet_direction`
- bin 수: `8`
- 의미: 가장 가까운 적 총알이 나를 기준으로 어느 방향에 있는지

### 15. `buffStateBin`
- 원본 값:
  - `self_has_attack_buff`
  - `enemy_has_attack_buff`
  - `self_attack_buff_ratio`
  - `enemy_attack_buff_ratio`
- bin 수: `4`
- 값:
  - `0`: 양쪽 다 버프 없음
  - `1`: 적만 버프 있음
  - `2`: 내가 버프 있음, 남은 시간이 적은 편
  - `3`: 내가 더 유리한 버프 상태

## Action Index

현재 `TabularQPolicy`의 액션 수는 `42`개입니다.

### 기본 대기
- `0`: `ACTION_IDLE`
  - 아무 행동도 하지 않음

### 절대 8방향 이동
- `1`: `ACTION_MOVE_UP`
- `2`: `ACTION_MOVE_UP_RIGHT`
- `3`: `ACTION_MOVE_RIGHT`
- `4`: `ACTION_MOVE_DOWN_RIGHT`
- `5`: `ACTION_MOVE_DOWN`
- `6`: `ACTION_MOVE_DOWN_LEFT`
- `7`: `ACTION_MOVE_LEFT`
- `8`: `ACTION_MOVE_UP_LEFT`

### 상대/엄폐물/아이템 기준 이동
- `9`: `ACTION_MOVE_TO_ENEMY`
  - 적 쪽으로 이동
- `10`: `ACTION_MOVE_AWAY_FROM_ENEMY`
  - 적에게서 멀어짐
- `11`: `ACTION_MOVE_TO_COVER`
  - 가장 가까운 엄폐물 쪽으로 이동
- `12`: `ACTION_MOVE_AWAY_FROM_COVER`
  - 엄폐물 반대 방향 이동
- `13`: `ACTION_MOVE_TO_ITEM`
  - 아이템 쪽으로 이동
- `14`: `ACTION_MOVE_AWAY_FROM_ITEM`
  - 아이템 반대 방향 이동

### 공격
- `15`: `ACTION_ATTACK`
  - 적 정중앙 조준 공격

### 절대 8방향 조준 공격
- `16`: `ACTION_ATTACK_UP`
- `17`: `ACTION_ATTACK_UP_RIGHT`
- `18`: `ACTION_ATTACK_RIGHT`
- `19`: `ACTION_ATTACK_DOWN_RIGHT`
- `20`: `ACTION_ATTACK_DOWN`
- `21`: `ACTION_ATTACK_DOWN_LEFT`
- `22`: `ACTION_ATTACK_LEFT`
- `23`: `ACTION_ATTACK_UP_LEFT`

### 적 기준 오프셋 조준 공격
- `24`: `ACTION_ATTACK_OFFSET_LEFT`
  - 적 기준 왼쪽으로 비껴 조준
- `25`: `ACTION_ATTACK_OFFSET_RIGHT`
  - 적 기준 오른쪽으로 비껴 조준
- `26`: `ACTION_ATTACK_OFFSET_FORWARD`
  - 적보다 조금 앞쪽으로 조준
- `27`: `ACTION_ATTACK_OFFSET_BACKWARD`
  - 적보다 조금 뒤쪽으로 조준

### 공격 복합 행동
- `28`: `ACTION_ATTACK_AND_CHASE`
  - 공격하면서 적 쪽으로 이동
- `29`: `ACTION_ATTACK_AND_RETREAT`
  - 공격하면서 적에게서 멀어짐

### 절대 8방향 대시
- `30`: `ACTION_DASH_UP`
- `31`: `ACTION_DASH_UP_RIGHT`
- `32`: `ACTION_DASH_RIGHT`
- `33`: `ACTION_DASH_DOWN_RIGHT`
- `34`: `ACTION_DASH_DOWN`
- `35`: `ACTION_DASH_DOWN_LEFT`
- `36`: `ACTION_DASH_LEFT`
- `37`: `ACTION_DASH_UP_LEFT`

### 상대/엄폐물/아이템 기준 대시
- `38`: `ACTION_DASH_TO_ENEMY`
  - 적 쪽으로 대시
- `39`: `ACTION_DASH_AWAY_FROM_ENEMY`
  - 적 반대 방향으로 대시
- `40`: `ACTION_DASH_TO_COVER`
  - 엄폐물 쪽으로 대시
- `41`: `ACTION_DASH_TO_ITEM`
  - 아이템 쪽으로 대시

## Raw Observation Fields Used Indirectly

아래 필드들은 상태 키에 그대로 들어가지는 않지만, bin 계산에 사용됩니다.

- `self_position`
- `enemy_position`
- `enemy_direction`
- `distance_to_enemy`
- `self_hp`
- `self_hp_max`
- `enemy_hp`
- `enemy_hp_max`
- `state`
- `enemy_state`
- `self_attack_cooldown_ratio`
- `self_dash_cooldown_ratio`
- `enemy_attack_cooldown_ratio`
- `enemy_dash_cooldown_ratio`
- `nearest_cover_distance`
- `cover_positions`
- `item_active`
- `self_item_distance`
- `enemy_item_distance`
- `enemy_bullet_count`
- `nearest_enemy_bullet_distance`
- `second_enemy_bullet_distance`
- `nearest_enemy_bullet_direction`
- `self_has_attack_buff`
- `enemy_has_attack_buff`
- `self_attack_buff_ratio`
- `enemy_attack_buff_ratio`

## Note

실제 정책 선택 시에는 현재 상태에서 불가능한 액션이 일부 후보에서 제외됩니다.

예:
- 공격 불가 상태에서는 공격 액션 일부 제외
- 대시 불가 상태에서는 대시 액션 제외
- 아이템이 없으면 아이템 관련 이동/대시 제외
