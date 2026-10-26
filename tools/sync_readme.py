#!/usr/bin/env python3
"""Check the separate English/Spanish quick starts. The old combined README is no longer generated."""
import pathlib,sys
ROOT=pathlib.Path(__file__).resolve().parent.parent

def main(check=False):
    english=(ROOT/'README.md').read_text();spanish=(ROOT/'LEEME.md').read_text()
    return 'href="LEEME.md"' in english and 'href="README.md"' in spanish and '<!-- BEGIN SPANISH' not in english and len(english.splitlines())<140 and len(spanish.splitlines())<140

if __name__=='__main__':
    if not main('--check' in sys.argv):print('Check the language links and keep each quick start below 140 lines.');sys.exit(1)
