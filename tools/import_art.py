#!/usr/bin/env python3
"""Import the supplied Deck Library PNG pack without changing the image pixels."""
import argparse,base64,hashlib,json,pathlib,struct,zipfile

ROOT=pathlib.Path(__file__).resolve().parent.parent
SOURCES={
    '01_icono_app_degradado_512x512.png':((512,512),('assets/icon.png','assets/steam/icon.png')),
    '03_isotipo_transparente_512x512.png':((512,512),('assets/brand.png',)),
    '04_logo_transparente_steam_1712x452.png':((1712,452),('assets/steam/logo.png',)),
    '05_portada_vertical_600x900.png':((600,900),('assets/steam/portrait.png',)),
    '07_portada_horizontal_920x430.png':((920,430),('assets/steam/banner.png',)),
    '08_banner_hero_limpio_1920x620.png':((1920,620),('assets/steam/hero.png',)),
}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive',type=pathlib.Path,help='deck_library_png_pack.zip')
    args=parser.parse_args();images={}
    with zipfile.ZipFile(args.archive) as archive:
        for name,(size,targets) in SOURCES.items():
            if archive.getinfo(name).file_size>20*1024*1024:raise ValueError('Image exceeds 20 MiB: '+name)
            data=archive.read(name)
            if not data.startswith(b'\x89PNG\r\n\x1a\n') or data[12:16]!=b'IHDR' or struct.unpack('>II',data[16:24])!=size:raise ValueError('Unexpected PNG dimensions: '+name)
            images[name]=data
    history_file=ROOT/'assets/steam/previous-defaults.json'
    history=json.loads(history_file.read_text()) if history_file.exists() else {'schema':1,'slots':{}}
    for slot,filename in {'portrait':'portrait.png','banner':'banner.png','hero':'hero.png','logo':'logo.png','icon':'icon.png'}.items():
        previous=ROOT/'assets/steam'/filename
        if previous.is_file():
            values=set(history['slots'].get(slot,[]));values.add(hashlib.sha256(previous.read_bytes()).hexdigest());history['slots'][slot]=sorted(values)
    history_file.write_text(json.dumps(history,indent=2)+'\n')
    for name,(_,targets) in SOURCES.items():
        for relative in targets:
            target=ROOT/relative;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(images[name]);print(relative)
    # Keep the existing desktop theme path and embed the exact supplied PNG.
    payload=base64.b64encode(images['01_icono_app_degradado_512x512.png']).decode('ascii')
    (ROOT/'assets/icon.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="512" height="512" viewBox="0 0 512 512"><image width="512" height="512" xlink:href="data:image/png;base64,'+payload+'"/></svg>\n')
    print('assets/icon.svg (PNG wrapper for desktop icon themes)')

if __name__=='__main__':main()
