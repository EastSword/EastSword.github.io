# 首页水墨侠客图

生成日期：2026-09-08。

- 模型：Tongyi-MAI/Z-Image-Turbo。
- 生成方式：模型官方 Hugging Face 免费演示服务 https://huggingface.co/spaces/Tongyi-MAI/Z-Image-Turbo 。没有使用付费 API，也不是古画素材拼贴。
- 官方模型页：https://huggingface.co/Tongyi-MAI/Z-Image-Turbo （模型卡标记 Apache-2.0）。
- 参数：1344 × 576，seed 88，steps 8，time shift 3。
- `assets/images/hero/warrior-original.webp`：生成图的 WebP 压缩版。
- `assets/images/hero/warrior-inkwash.webp`：首页使用版本，左侧山景及上、下、右边缘柔和淡出为透明，以融入原有背景，人物主体保持清晰。
- 重新处理边缘：`python3 scripts/prepare_hero_art.py`（需要 Pillow）。

## Prompt

A majestic Chinese wuxia ink-wash painting, panoramic cinematic banner, horizontal composition. On the RIGHT THIRD stands one powerful heroic Chinese swordsman on a solid jagged mountain ledge. Full body visible, broad shoulders, strong upright stance with feet firmly planted, dignified and courageous, a living human hero. He wears flowing ivory-white hanfu robes with bold black ink folds, a dark belt, and a wide bamboo hat. His face is partly visible and lit by daylight, calm and resolute. One hand grips a long straight Chinese jian sword pointing diagonally down beside the rock. Wind drives his long white cloak toward the right edge in great sweeping brush strokes. Monumental mountains and bright silver mist behind the hero, strong natural daylight and dramatic ink contrast. The LEFT HALF is quiet deep charcoal-green mountain shadow and spacious dark negative space, reserved for website typography, no objects in the left foreground. Expressive broad wet ink brushwork, textured ink washes and dry brush edges, restrained pale gold highlights, elegant Chinese landscape painting, tremendous strength and heroic grandeur. The figure belongs naturally to the landscape with weight, depth, and a grounded shadow. A single continuous painting without borders, no writing, no calligraphy, no logos, no watermark. Not a woodcut, not line art, not a ghost, not horror, not skeleton, not flat cutout, not glowing eyes, not a collage.
