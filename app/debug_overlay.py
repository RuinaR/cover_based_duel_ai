import pygame


class DebugOverlay:
    def __init__(self) -> None:
        self._visible = True
        self._font = None
        self._titleFont = None
        self._padding = 10
        self._lineHeight = 18
        self._width = 380

    def handleEvent(self, event) -> None:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_F1:
            self._visible = not self._visible

    def render(self, screen, frameResult=None) -> None:
        if not self._visible:
            return

        self._ensureFonts()
        lines = self._buildLines(frameResult)
        boxHeight = self._padding * 2 + 28 + (len(lines) * self._lineHeight)
        panel = pygame.Surface((self._width, boxHeight), pygame.SRCALPHA)
        panel.fill((8, 12, 18, 190))
        pygame.draw.rect(panel, (90, 210, 255, 220), panel.get_rect(), 2, border_radius=10)

        title = self._titleFont.render("Debug Overlay  [F1]", True, (210, 240, 255))
        panel.blit(title, (self._padding, self._padding))

        y = self._padding + 28
        for text, color in lines:
            surface = self._font.render(text, True, color)
            panel.blit(surface, (self._padding, y))
            y += self._lineHeight

        screen.blit(panel, (12, 12))

    def _ensureFonts(self) -> None:
        if self._font is None:
            self._font = pygame.font.SysFont("consolas", 15)
        if self._titleFont is None:
            self._titleFont = pygame.font.SysFont("consolas", 18, bold=True)

    def _buildLines(self, frameResult) -> list[tuple[str, tuple[int, int, int]]]:
        if frameResult is None:
            return [
                ("Waiting for GameScene frame...", (180, 190, 200)),
            ]

        lines = [
            (f"frame: {frameResult.frameIndex}", (255, 230, 140)),
            (
                f"done: {frameResult.done}  winner: {frameResult.winner}",
                (255, 160, 160) if frameResult.done else (170, 220, 170),
            ),
            (
                f"reward A/B: {frameResult.rewards.get('ai_a', 0.0):.1f} / {frameResult.rewards.get('ai_b', 0.0):.1f}",
                (220, 220, 220),
            ),
        ]

        obsA = frameResult.nextObservations.get("ai_a", {})
        obsB = frameResult.nextObservations.get("ai_b", {})
        lines.extend(
            [
                (
                    f"A hp:{obsA.get('self_hp', '?')}/{obsA.get('self_hp_max', '?')} state:{obsA.get('state', '?')} dist:{obsA.get('distance_to_enemy', 0.0):.1f}",
                    (255, 120, 120),
                ),
                (
                    f"B hp:{obsB.get('self_hp', '?')}/{obsB.get('self_hp_max', '?')} state:{obsB.get('state', '?')} dist:{obsB.get('distance_to_enemy', 0.0):.1f}",
                    (120, 180, 255),
                ),
                ("", (220, 220, 220)),
                ("call stack:", (255, 230, 140)),
            ]
        )

        for entry in frameResult.callStack:
            lines.append((entry, (210, 220, 230)))

        if frameResult.episodeSummary:
            lines.extend(
                [
                    ("", (220, 220, 220)),
                    (frameResult.episodeSummary, (255, 210, 150)),
                ]
            )

        return lines
