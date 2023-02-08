
# AI Opera

This repo contains the code to generate text and melody for the AI singing voice in the AI-generated opera [Chasing Waterfalls](https://www.semperoper.de/en/whats-on/schedule/stid/chasing-waterfalls-en/62127.html). 

## Proof of concept — Alert ⚠️

Due to intellectual property reasons, only a very early version of the codebase (`v.0.3`) is shown. This doesn't represent the last iteration used in production (`v.1.3.6`). As a result, the entire MLOps CI/CD pipeline is absent, as well as the refined versions of the algorithms.

The repository should only function as a proof-of-concept to the readers, to illustrate how it is possible to generate text and melody using different ML models.

## Melody and text generation pipeline

### 1. Setup

1- Clone the repo using the `--recursive` flag for submodules

2- Install requirements: 
```
pip install -r requirements.txt
```
### 2. Execution
1- Run `main.py`

A directory with a unique identifier (in the format of `YEAR-MONTH-DAY_HOUR_MIN_SEC` will be created under the `out_files` folder, with:

```
unique_generation_id
└───part_A
│   │   melody.mid
│   │   melody_pp.mid
│   │   lyrics.txt
│   │   txt.txt
│   │   txt_punctuation.txt
│   │   txt_word.txt
└───part_B
│   │   ...
└───part_C
│   │   ...
└───temp
│   └───part_A
│   │   │   ...
│   └───part_B
│   │   │   ...
│   └───part_C
│   │   │   ...
```

[I] A subdirectory for every `part` of scene 5, containing:

1. Generated melody file `melody.mid`
2. Generated melody file post processed `melody_pp.mid`
3. Generated lyrics `lyrics.txt`
4. Generated lyrics with syllables and phonemes boundaries: `txt.txt`
5. Generated lyrics with syllables and phonemes boundaries, as well as punctuation as special phoneme: `txt_punctuation.txt`
6. Generated lyrics with syllables and phonemes boundaries, as well as word boundaries: `txt_word.txt`

[II] A subdirectory called `temp` containing temporary files created while generating the complete melody.

The files `2, 3, 5` of every `part` can be used as direct input for the voice synthesis networks.

Parts are called: `part_A`, `part_B`, `part_C`

### 3. Global parameters

Global parameters are exposed in the `global.yaml` file, and can be changed if necessary.

### 4. Notes

This repo uses the CMU dict to represent phonemes, and to compute syllables boundaries.

### 5. Contact

For any question, or problem contact Pietro: pietro@klingklangklong.com
