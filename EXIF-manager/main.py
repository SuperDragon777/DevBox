import argparse
import shutil
from pathlib import Path

from PIL import Image
from PIL.ExifTags import TAGS


TAGS_BY_NAME = {name.lower(): tag_id for tag_id, name in TAGS.items()}


def humanize_exif_tag(tag_id, tag_value):
    tag_name = TAGS.get(tag_id, str(tag_id))
    text = str(tag_value)
    if len(text) > 200:
        text = text[:197] + "..."
    return tag_name, text


def read_exif(path: Path):
    try:
        with Image.open(path) as img:
            exif = img.getexif()
            if not exif:
                return {}
            return dict(exif)
    except Exception as exc:
        raise RuntimeError(f"Failed to read EXIF from file '{path}': {exc}") from exc


def cmd_show(paths):
    for p_str in paths:
        path = Path(p_str)
        if not path.is_file():
            print(f"[!] File not found: {path}")
            continue
        print(f"\n=== {path} ===")
        try:
            exif = read_exif(path)
        except RuntimeError as e:
            print(e)
            continue
        if not exif:
            print("No EXIF metadata.")
            continue
        for tag_id, value in exif.items():
            tag_name, text = humanize_exif_tag(tag_id, value)
            print(f"{tag_name} ({tag_id}): {text}")


def strip_exif(input_path: Path, output_path: Path):
    try:
        with Image.open(input_path) as img:
            data = list(img.getdata())
            mode = img.mode
            size = img.size
        img_clean = Image.new(mode, size)
        img_clean.putdata(data)
        img_clean.save(output_path)
    except Exception as exc:
        raise RuntimeError(f"Failed to remove EXIF from file '{input_path}': {exc}") from exc


def resolve_tag_id(tag: str) -> int:
    if tag.isdigit():
        return int(tag)
    key = tag.strip().lower()
    if key in TAGS_BY_NAME:
        return TAGS_BY_NAME[key]
    raise ValueError(f"Unknown EXIF tag: {tag}")


def apply_exif_edits(src: Path, dst: Path, updates: dict[int, str]):
    try:
        with Image.open(src) as img:
            exif = img.getexif()
            if exif is None:
                exif = Image.Exif() if hasattr(Image, "Exif") else {}
            for tag_id, value in updates.items():
                exif[tag_id] = value
            exif_bytes = exif.tobytes() if hasattr(exif, "tobytes") else exif
            img.save(dst, exif=exif_bytes)
    except Exception as exc:
        raise RuntimeError(f"Failed to modify EXIF in file '{src}': {exc}") from exc


def cmd_clear(paths, in_place: bool, backup: bool, suffix: str | None, output: str | None):
    out_dir = Path(output) if output else None
    if out_dir:
        out_dir.mkdir(parents=True, exist_ok=True)
    for p_str in paths:
        src = Path(p_str)
        if not src.is_file():
            print(f"[!] File not found: {src}")
            continue
        try:
            if out_dir:
                dst = out_dir / src.name
            elif in_place:
                dst = src
            else:
                dst = src.with_name(src.stem + "_noexif" + src.suffix)
            if dst == src and backup:
                backup_suffix = suffix or ".bak"
                backup_path = src.with_name(src.name + backup_suffix)
                shutil.copy2(src, backup_path)
                print(f"[i] Backup created: {backup_path}")
            strip_exif(src, dst)
            print(f"[+] EXIF removed: {src} -> {dst}")
        except RuntimeError as e:
            print(e)


def cmd_edit(paths, edits: list[str], in_place: bool, backup: bool, suffix: str | None, output: str | None):
    if not edits:
        print("[!] No changes specified (--set TAG=VALUE).")
        return
    updates: dict[int, str] = {}
    for item in edits:
        if "=" not in item:
            print(f"[!] Invalid parameter format: {item}. Expected TAG=VALUE.")
            continue
        key, value = item.split("=", 1)
        try:
            tag_id = resolve_tag_id(key)
        except ValueError as e:
            print(e)
            continue
        updates[tag_id] = value
    if not updates:
        print("[!] No valid tags to modify.")
        return
    out_dir = Path(output) if output else None
    if out_dir:
        out_dir.mkdir(parents=True, exist_ok=True)
    for p_str in paths:
        src = Path(p_str)
        if not src.is_file():
            print(f"[!] File not found: {src}")
            continue
        try:
            if out_dir:
                dst = out_dir / src.name
            elif in_place:
                dst = src
            else:
                dst = src.with_name(src.stem + "_edited" + src.suffix)
            if dst == src and backup:
                backup_suffix = suffix or ".bak"
                backup_path = src.with_name(src.name + backup_suffix)
                shutil.copy2(src, backup_path)
                print(f"[i] Backup created: {backup_path}")
            apply_exif_edits(src, dst, updates)
            print(f"[+] EXIF updated: {src} -> {dst}")
        except RuntimeError as e:
            print(e)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="EXIF-manager",
        description="Utility for viewing and managing EXIF metadata of photos.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    show_p = subparsers.add_parser(
        "show",
        help="Show EXIF metadata of image(s).",
    )
    show_p.add_argument(
        "paths",
        nargs="+",
        help="Path(s) to image files.",
    )
    clear_p = subparsers.add_parser(
        "clear",
        help="Remove EXIF metadata from image(s).",
    )
    clear_p.add_argument(
        "paths",
        nargs="+",
        help="Path(s) to image files.",
    )
    clear_p.add_argument(
        "-i",
        "--in-place",
        action="store_true",
        help="Overwrite original file (by default a new *_noexif.ext file is created).",
    )
    clear_p.add_argument(
        "-b",
        "--backup",
        action="store_true",
        help="Create backup before overwrite (works only with --in-place).",
    )
    clear_p.add_argument(
        "--backup-suffix",
        default=None,
        help="Suffix for backup (default '.bak'). Final name will be original.ext.suffix.",
    )
    clear_p.add_argument(
        "-o",
        "--output",
        default=None,
        help="Directory to save files without EXIF. If set, files are not overwritten in place.",
    )
    edit_p = subparsers.add_parser(
        "edit",
        help="Edit EXIF metadata of image(s).",
    )
    edit_p.add_argument(
        "paths",
        nargs="+",
        help="Path(s) to image files.",
    )
    edit_p.add_argument(
        "-s",
        "--set",
        action="append",
        metavar="TAG=VALUE",
        help="Set EXIF tag value (can be specified multiple times). TAG may be a name or numeric ID.",
    )
    edit_p.add_argument(
        "-i",
        "--in-place",
        action="store_true",
        help="Overwrite original file (by default a new *_edited.ext file is created).",
    )
    edit_p.add_argument(
        "-b",
        "--backup",
        action="store_true",
        help="Create backup before overwrite (works only with --in-place).",
    )
    edit_p.add_argument(
        "--backup-suffix",
        default=None,
        help="Suffix for backup (default '.bak').",
    )
    edit_p.add_argument(
        "-o",
        "--output",
        default=None,
        help="Directory to save modified files. If set, files are not overwritten in place.",
    )
    return parser


def main(argv=None):
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    if args.command == "show":
        cmd_show(args.paths)
    elif args.command == "clear":
        cmd_clear(
            paths=args.paths,
            in_place=args.in_place,
            backup=args.backup,
            suffix=args.backup_suffix,
            output=args.output,
        )
    elif args.command == "edit":
        cmd_edit(
            paths=args.paths,
            edits=args.set or [],
            in_place=args.in_place,
            backup=args.backup,
            suffix=args.backup_suffix,
            output=args.output,
        )
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

