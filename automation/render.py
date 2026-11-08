from pathlib import Path
import json
import shutil
import subprocess

from PIL import Image, ImageDraw, ImageFont

WIDTH, HEIGHT = 1080, 1920
FPS, SECONDS = 30, 7
INK, MUTED = '#132924', '#49605a'
BACKGROUND = '#f5f6f0'
FONT_PATHS = {
    'heading': ('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
                'C:/Windows/Fonts/segoeuib.ttf'),
    'code': ('/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf',
             'C:/Windows/Fonts/consola.ttf'),
}


def fitted_font(draw, lines, width, size, family='heading'):
    path = next(path for path in FONT_PATHS[family] if Path(path).is_file())
    font = ImageFont.truetype(path, size)
    while max(draw.textlength(line, font=font) for line in lines) > width:
        size -= 2
        font = ImageFont.truetype(path, size)
    return font


def draw_card(draw, top, label, value, highlight, color, fill, code_font):
    draw.rounded_rectangle((76, top, 1004, top + 284), 30, fill='white',
                           outline='#dce4dc', width=3)
    label_font = fitted_font(draw, [label], 820, 41)
    draw.text((120, top + 28), label, font=label_font, fill=color)
    for index, line in enumerate(value.splitlines()):
        y = top + 113 + index * 60
        x = 120
        if highlight in line:
            left, match, right = line.partition(highlight)
            start = x + draw.textlength(left, font=code_font)
            end = start + draw.textlength(match, font=code_font)
            draw.rounded_rectangle((start - 4, y - 3, end + 4, y + 51), 8, fill=fill)
            draw.text((start, y), match, font=code_font, fill=color)
            draw.text((x, y), left, font=code_font, fill=INK)
            draw.text((end, y), right, font=code_font, fill=INK)
        else:
            draw.text((x, y), line, font=code_font, fill=INK)


def render(directory='run'):
    folder = Path(directory)
    plan = json.loads((folder / 'plan.json').read_text(encoding='utf-8'))
    capture = json.loads((folder / 'capture.json').read_text(encoding='utf-8'))
    before, after = capture['before'], capture['after']
    secret = plan['example']['secret']
    if before != plan['example']['text'] or secret in after or '[REDACTED]' not in after:
        raise ValueError('Capture did not verify this redaction')

    def frame(show_after, show_link):
        image = Image.new('RGB', (WIDTH, HEIGHT), BACKGROUND)
        draw = ImageDraw.Draw(image)
        label = plan['example']['label'].upper()
        draw.text((78, 225), label, font=fitted_font(draw, [label], 900, 38), fill=MUTED)
        title = plan['hook']
        draw.text((76, 304), title, font=fitted_font(draw, [title], 928, 83), fill=INK)
        code_font = fitted_font(draw, before.splitlines() + after.splitlines(), 840, 48, 'code')
        draw_card(draw, 480, 'BEFORE', before, secret, '#9d3525', '#ffebe5', code_font)
        if show_after:
            draw_card(draw, 822, 'AFTER PASTING', after, '[REDACTED]', '#176644', '#def6e6', code_font)
            line = 'Secret hidden. Context kept.'
            draw.text((78, 1165), line, font=fitted_font(draw, [line], 920, 51), fill=INK)
        if show_link:
            cta = 'Try PasteGuard free · link in bio'
            draw.text((78, 1328), cta, font=fitted_font(draw, [cta], 920, 42), fill='#176644')
        note = 'Fake data · review before sharing'
        draw.text((78, 1450), note, font=fitted_font(draw, [note], 920, 30), fill=MUTED)
        return image

    intro, reveal, close = frame(False, False), frame(True, False), frame(True, True)
    intro.save(folder / 'cover.jpg', quality=95)
    for second, still in ((0, intro), (2, reveal), (5, close)):
        still.save(folder / f'proof-{second * FPS}.jpg', quality=95)

    exe = shutil.which('ffmpeg')
    if not exe:
        import imageio_ffmpeg
        exe = imageio_ffmpeg.get_ffmpeg_exe()
    video = folder / 'video.mp4'
    with (folder / 'encode.log').open('wb') as log:
        with subprocess.Popen(
            [exe, '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{WIDTH}x{HEIGHT}',
             '-r', str(FPS), '-i', 'pipe:0', '-an', '-c:v', 'libx264', '-preset', 'veryfast',
             '-crf', '19', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(video)],
            stdin=subprocess.PIPE, stderr=log, stdout=log,
        ) as process:
            for still, frames in ((intro, 42), (reveal, 108), (close, 60)):
                pixels = still.tobytes()
                for _ in range(frames):
                    process.stdin.write(pixels)
            process.stdin.close()
            if process.wait():
                raise RuntimeError('Video encoding failed')
    subprocess.run([exe, '-v', 'error', '-i', str(video), '-f', 'null', '-'],
                   check=True, capture_output=True)
    (folder / 'caption.txt').write_text(plan['caption'], encoding='utf-8')
    (folder / 'verification.json').write_text(json.dumps({
        'seconds': SECONDS, 'width': WIDTH, 'height': HEIGHT, 'fps': FPS,
        'audio': 'none', 'decode_passed': True,
        'source': 'Text reproduced from a verified clipboard paste on the live demo using fake data',
    }, indent=2), encoding='utf-8')


if __name__ == '__main__':
    render()
