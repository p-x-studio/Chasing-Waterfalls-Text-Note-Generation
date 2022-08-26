"""
This script handles the text generation using GPT3 as well as the syllables boundaries computation
"""
import os
import logging
import re
import pronouncing
import openai
import random
import string
import syllabify.syllable3

PUNCTUATION_SYMBOL = '<punctuation>'

def expand_contractions(text):
  """
  Finds and expand contractions of the most common english ones contraction list from file

  Parameters
  ----------
  text : string
      The text to expand

  Returns
  -------
  string
      The expanded text
  """

  c_list = {
    "a'ight": "alright",
    "ain't": "am not",
    "amn't": "am not",
    "'n'": "and",
    "arencha": "aren't you",
    "aren't": "are not",
    "'bout": "about",
    "can't": "cannot",
    "cap'n": "captain",
    "'cause": "because",
    "'cept": "except",
    "could've": "could have",
    "couldn't": "could not",
    "couldn't've": "could not have",
    "cuppa": "cup of",
    "dammit": "damn it",
    "daren't": "dare not",
    "daresn't": "dare not",
    "dasn't": "dare not",
    "didn't": "did not",
    "doesn't": "does not",
    "don't": "do not",
    "dunno": "don't know",
    "d'ye": "do you",
    "d'ya": "do you",
    "e'en": "even",
    "e'er": "ever",
    "'em": "them",
    "everybody's": "everybody is",
    "everyone's": "everyone is",
    "finna": "fixing to",
    "fo'c'sle": "forecastle",
    "'gainst": "against",
    "g'day": "good day",
    "gimme": "give me",
    "giv'n": "given",
    "gi'z": "give us",
    "gonna": "going to",
    "gon't": "go not",
    "gotta": "got to",
    "hadn't": "had not",
    "had've": "had have",
    "hasn't": "has not",
    "haven't": "have not",
    "he'd": "he had",
    "he'll": "he shall",
    "helluva": "hell of a",
    "he's": "he has",
    "here's": "here is",
    "how'd": "how did",
    "howdy": "how do you do",
    "how'll": "how will",
    "how're": "how are",
    "how's": "how has",
    "i'd": "I had",
    "i'd've": "I would have",
    "i'd'nt": "I would not",
    "i'd'nt've": "I would not have",
    "i'll": "I shall",
    "i'm": "I am",
    "imma": "I am about to",
    "i'm'o": "I am going to",
    "innit": "isn't it",
    "i've": "I have",
    "isn't": "is not",
    "it'd": "it would",
    "it'll": "it shall",
    "it's": "it has",
    "Idunno": "I don't know",
    "kinda": "kind of",
    "let's": "let us",
    "loven't": "love not",
    "ma'am": "madam",
    "mayn't": "may not",
    "may've": "may have",
    "methinks": "I think",
    "mightn't": "might not",
    "might've": "might have",
    "mustn't": "must not",
    "mustn't've": "must not have",
    "must've": "must have",
    "'neath": "beneath",
    "needn't": "need not",
    "nal": "and all",
    "ne'er": "never",
    "o'clock": "of the clock",
    "o'er": "over",
    "ol'": "old",
    "ought've": "ought have",
    "oughtn't": "ought not",
    "oughtn't've": "ought not have",
    "'round": "around",
    "'s": "is",
    "shalln't": "shall not",
    "shan't": "shall not",
    "she'd": "she had",
    "she'll": "she shall",
    "she's": "she has",
    "should've": "should have",
    "shouldn't": "should not",
    "shouldn't've": "should not have",
    "somebody's": "somebody has",
    "someone's": "someone has",
    "something's": "something has",
    "so're": "so are",
    "so's": "so is",
    "so've": "so have",
    "that'll": "that shall",
    "that're": "that are",
    "that's": "that has",
    "that'd": "that would",
    "there'd": "there had",
    "there'll": "there shall",
    "there're": "there are",
    "there's": "there has",
    "these're": "these are",
    "these've": "these have",
    "they'd": "they had",
    "they'll": "they shall",
    "they're": "they are",
    "they've": "they have",
    "this's": "this has",
    "those're": "those are",
    "those've": "those have",
    "'thout": "without",
    "'til": "until",
    "'tis": "it is",
    "to've": "to have",
    "'twas": "it was",
    "'tween": "between",
    "'twere": "it were",
    "w'all": "we all",
    "w'at": "we at",
    "wanna": "want to",
    "wasn't": "was not",
    "we'd": "we had",
    "we'd've": "we would have",
    "we'll": "we shall",
    "we're": "we are",
    "we've": "we have",
    "weren't": "were not",
    "whatcha": "what are you what about you",
    "what'd": "what did",
    "what'll": "what shall",
    "what're": "what are",
    "what's": "what has",
    "what've": "what have",
    "when's": "when has",
    "where'd": "where did",
    "where'll": "where shall",
    "where're": "where are",
    "where's": "where has",
    "where've": "where have",
    "which'd": "which had",
    "which'll": "which shall",
    "which're": "which are",
    "which's": "which has",
    "which've": "which have",
    "who'd": "who would",
    "who'd've": "who would have",
    "who'll": "who shall",
    "who're": "who are",
    "who's": "who has",
    "who've": "who have",
    "why'd": "why did",
    "why're": "why are",
    "why's": "why has",
    "willn't": "will not",
    "won't": "will not",
    "wonnot": "will not",
    "would've": "would have",
    "wouldn't": "would not",
    "wouldn't've": "would not have",
    "y'ain't": "you are not",
    "y'all": "you all",
    "y'all'd've": "you all would have",
    "y'all'd'n't've": "you all would not have",
    "y'all're": "you all are",
    "y'all'ren't": "you all are not",
    "y'at": "you at",
    "yes'm": "yes ma'am",
    "y'know": "you know",
    "yessir": "yes sir",
    "you'd": "you had",
    "you'll": "you shall",
    "you're": "you are",
    "you've": "you have",
    "when'd": "when did",
  }

  c_re = re.compile('(%s)' % '|'.join(c_list.keys()))

  def replace(match):
    return c_list[match.group(0)]

  return c_re.sub(replace, text.lower())

def list_right_index(alist, value):
  """
  Finds the index of the rightmost element

  Parameters
  ----------
  alist : list
      The list to search
  value
      The value to search in the list

  Returns
  -------
  int
      The index of the element
  """
  return len(alist) - alist[-1::-1].index(value) -1

def is_cmu_valid(text):
  """
  Checks if all the words in a text are present in the CMU dict used by sillabify

  Parameters
  ----------
  text : str
      The text to check

  Returns
  -------
  dict
      A dictionary with the following keys:
        - success : boolean, if true all the words are valid
        - message : str, if success == true will be empty,
                    otherwise will contain the word that does not belong to CMU
  """
  text = text.translate(str.maketrans('', '', string.punctuation)) # remove punctuation
  words = text.split()
  ret = {'success': True, 'message': ''}
  
  for word in words:
    word = word.strip()
    phoneme_list = syllabify.syllable3.CMUtranscribe(word)

    if not phoneme_list:
      ret['success'] = False
      ret['message'] = word
  
  return ret

def phoneme_list_to_csd(phoneme_list):
  """
  Converts a phoneme list returned by sillabify in the format required for csd to work

  Parameters
  ----------
  phoneme_list : list
      List of phonemes returned by sillabify

  Returns
  -------
  str
      The phonemes in csd format
  """
  ret = ''
            
  for ph in phoneme_list.phoneme_list:
    ret += ph.phoneme + ' '
  
  ret = ret.strip()
  ret = ret.replace(' ', '_')

  return ret

def compute_csd_text(text):
  """
  Given an input text, this function transforms it in the format used in the CSD dataset 
  so that it can be used as input for the MLP singer model

  This means:

  - It removes any punctuation sign
  - It divides the text in syllables, and compute the phonemes (using the CMU dict)
  - It adds a special punctuation phoneme

  Parameters
  ----------
  text : str
      The input text to be processed

  Returns
  -------
  tuple (str, str)
      - The input text stripped and without punctuation symbol
      - The input text divided in syllables and phonemes, as in the CSD format
  """
  # replace punctuation marks with a special phoneme <punctuation>
  text = text.replace(".", PUNCTUATION_SYMBOL)
  # text = text.replace(",", PUNCTUATION_SYMBOL)
  text = text.replace("?", PUNCTUATION_SYMBOL)
  text = text.replace("!", PUNCTUATION_SYMBOL)
  text = text.replace(":", PUNCTUATION_SYMBOL)
  text = text.replace(";", PUNCTUATION_SYMBOL)

  text = text.replace(f'{PUNCTUATION_SYMBOL}{PUNCTUATION_SYMBOL}', PUNCTUATION_SYMBOL) # replace double punctuation symbols with just one
  text = text.replace("-", " ") # separate dashed words in two with a space
  text = re.sub(r'\n+', '\n', text) # replace multiple \n with a single one
  text = re.sub(r'\s+', ' ', text) # replace multiple spaces with a single one
  text = re.sub(r'\bai\b', 'ae ai', text, flags=re.IGNORECASE) # change word AI to phonemes that are more recognizable

  words = text.split()
  syll_and_phonemes = ''

  for word in words:
    punctuation_present = False
    composed_word = False

    if PUNCTUATION_SYMBOL in word:
      word = word.replace(PUNCTUATION_SYMBOL, "")
      punctuation_present = True

    # remove extra symbols a word might have
    word = word.translate(str.maketrans('', '', string.punctuation))

    if not word.strip() == False: # if the word is not an empty word
      # generate phonemes and syllables boundaries
      syllable = syllabify.syllable3.generate(word.rstrip())

      if syllable:
        # convert syllables in csd format
        for syll in syllable:
          if len(syll) > 1:
            composed_word = True

          if composed_word:
            syll_and_phonemes += '<word>'

          for s in syll:
            csd_syll_list = []

            if s.has_onset():
              onset = s.get_onset()
              csd_syll_list.append(phoneme_list_to_csd(onset))

            if s.has_nucleus():
              nucleus = s.get_nucleus()
              csd_syll_list.append(phoneme_list_to_csd(nucleus))
            
            if s.has_coda():
              coda = s.get_coda()
              csd_syll_list.append(phoneme_list_to_csd(coda))

            csd_syll = '_'.join(csd_syll_list)
            syll_and_phonemes += csd_syll + ' '

          if composed_word:
            syll_and_phonemes = syll_and_phonemes[:-1] + '</word> '

        if punctuation_present:
          syll_and_phonemes += f'{PUNCTUATION_SYMBOL} '
      else:
        logging.warning(f"Couldn't phonemize word: {repr(word)}")
  
  text = text.strip()
  syll_and_phonemes = syll_and_phonemes.strip()

  return text, syll_and_phonemes

def generate_text(pitches_count, 
                  global_var,
                  part_name,
                  prompt_append = '',
                  include_prompt_text = False, 
                  temperature = 0.7, top_p = 1,
                  frequency_penalty = 0,
                  presence_penalty = 0,
                  max_trials = 100):
  """
  Generates text using GPT3 with a number of syllables equal to the input pitches count, and write it to files

  Parameters
  ----------
  pitches_count : int
      The number of notes generated from the melody transformer
  global_var : dict
      The dictionary containing the global variables 
  part_name : str
      The name of the current macro-part
  prompt_append : str
      Additional text to be appended to the prompt
      This is used to give sequel to the different generted macro-parts
  include_prompt_text : bool (optional, default: False)
      If true, includes input_prompt as part of the output
      If false, only uses input_prompt to guide the generation but is excluded from the output
  temperature : float (optional, default: 0.7)
      Temperature parameter for GPT3
  top_p : float (optional, default: 1)
      Top P parameter for GPT3
  frequency_penalty : float (optional, default: 0)
      Frequency penalty parameter for GPT3
  presence_penalty : float (optional, default: 0)
      Presence penalty parameter for GPT3
  max_trials : int (optional, default: 100)
      Maxium amount of request to be done to GPT3

  Returns
  -------
  tuple (str, str, str, str)
      - The input text stripped and without punctuation symbol
      - The input text divided in syllables and phonemes, as in the CSD format
      - The input text divided in syllables and phonemes, as in the CSD format
        with added punctuation as special phoneme
      - The input text divided in syllables and phonemes, as in the CSD format
        with added word boundaries as special phoneme

  If the generation has invalid words not present in the CMU dictionary, then returns (0, 0, 0, 0)
  If the generation requires more than "max_trials" request then returns (-1, -1, -1, -1)
  """

  possible_continuations = ["the", "if", "when", "what", "how", "where", "which", "and", "or", "but", "so", "yet", "after", "although", "as", "as if", "as long as", "as much as", "as soon as", "because", "before", "even if", "even though", "unless", "while", "perhaps"]
  
  command = global_var['gpt3_command']
  seed = random.choice(global_var['gpt3_seed'])
  input_prompt = f'{command}\n\n{"" if seed == None else seed} {prompt_append}'

  prev_syll_count = 0

  logging.info(f'Input prompt: {repr(input_prompt)}')
  
  if include_prompt_text:
    cut_point = len(command)
  else:
    cut_point = len(input_prompt)

  for i in range(0, max_trials): # main generation loop
    response = openai.Completion.create(
      engine='text-davinci-002',
      prompt=input_prompt,
      temperature=temperature,
      max_tokens=512,
      top_p=top_p,
      frequency_penalty=frequency_penalty,
      presence_penalty=presence_penalty,
      stop=['.', '!', '?']
    )

    response_text = response['choices'][0]['text'] + '.' # select completion text from response

    # expand contractions in text
    response_text = expand_contractions(response_text)
    # remove \n and multiple white spaces
    response_text = re.sub(r'\n+', ' ', response_text)
    response_text = re.sub(r'\s+', ' ', response_text)
    
    input_prompt += response_text # append it to the previous text
    input_csd_text = input_prompt[cut_point:] # cut at cut_point

    # check if all the words are phonemizable
    cmu_valid = is_cmu_valid(input_csd_text)
    if not cmu_valid['success']:
      logging.warning(f'Invalid words detected in text generation. Invalid word: {repr(cmu_valid["message"])}')
      return (0, 0, 0, 0)

    text, syll_and_phonemes = compute_csd_text(input_csd_text) # compute CSD text
    
    # remove punctuation before a string
    text = text.strip()
    if text.strip()[0] == '<':
      text = text.replace('<punctuation>', '', 1)
    
    # with only punctuation
    syllables_punctuation = syll_and_phonemes.replace('<word>', '').replace('</word>', ' ')
    syllables_punctuation = re.sub(r'\s+', ' ', syllables_punctuation)
    syllables_punctuation = syllables_punctuation.strip()

    # without punctuation and words
    syllables_pure = syllables_punctuation.replace(f'{PUNCTUATION_SYMBOL}', '')
    syllables_pure = re.sub(r'\s+', ' ', syllables_pure)
    syllables_pure = syllables_pure.strip()

    # with only words
    syllables_word = syll_and_phonemes.replace(f'{PUNCTUATION_SYMBOL}', '')
    syllables_word = re.sub(r'\s+', ' ', syllables_word)
    syllables_word = re.sub(r'\bEY AY\b', '<word>EY AY</word>', syllables_word) # special case for word AI
    syllables_word = syllables_word.strip()

    # syllables count
    syllables_pure_split = syllables_pure.split(' ')
    syllables_pure_split[:] = [x for x in syllables_pure_split if x]
    current_syll_count = len(syllables_pure_split)

    logging.info(f'Current syllable count: {current_syll_count}')

    if current_syll_count >= pitches_count: # check if there is the need to generate more text
      # write text to output files
      out_path = os.path.join(global_var['auxiliary_temp_path'], part_name)
      out_lyrics_file = os.path.join(out_path, 'lyrics.txt')
      out_txt_file = os.path.join(out_path, 'txt.txt')
      out_txt_punctuation_file = os.path.join(out_path, 'txt_punctuation.txt')
      out_txt_word_file = os.path.join(out_path, 'txt_word.txt')

      logging.info(f'Written lyrics file at {out_lyrics_file}')
      with open(out_lyrics_file, 'w') as o:
        o.write(text)
      
      logging.info(f'Written txt file at {out_txt_file}')
      with open(out_txt_file, 'w') as o:
        o.write(syllables_pure)

      logging.info(f'Written txt with punctuation file at {out_txt_punctuation_file}')
      with open(out_txt_punctuation_file, 'w') as o:
        o.write(syllables_punctuation)
      
      logging.info(f'Written txt with word file at {out_txt_word_file}')
      with open(out_txt_word_file, 'w') as o:
        o.write(syllables_word)

      # return compued values
      return text, syllables_pure, syllables_punctuation, syllables_word
    else: # if there is the need to generate more text
      response_finish_reason = response['choices'][0]['finish_reason']

      if response_finish_reason == 'stop': # check if finish reason is stop
        # check if the model is stuck
        if current_syll_count == prev_syll_count:
          # if yes, add continuation word
          random_continuation = random.choice(possible_continuations).capitalize()
          input_prompt += ' ' + random_continuation

          logging.info(f'Detected stuck. Adding: {random_continuation}')
    
    prev_syll_count = current_syll_count
  
  # Critical error - max trials exceeded
  return (-1, -1, -1, -1)