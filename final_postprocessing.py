"""
This script handles the final post processing steps for the generated melody.
This includes resizing note lengths and adding pauses in order to enable 
audio snippetting, and more understandability of the lyrics.
"""

import pretty_midi
import os
import logging
import random
import yaml
from yaml.loader import SafeLoader
from melody_generation import write_midi_out

def phoneme_to_length(phoneme, start, time_mult = 1):
  """
  Given the length of a phoneme, it calculates the right ending time of the note
  This is done in order to ensure more understandability of lyrics
  
  Parameters
  ----------
  phoneme : str
      The input phoneme 
  start : int
      The start time in seconds of the note
  mult : float
      A multiplier to make all the note faster or slower

  Returns
  -------
  int
      The end time in seconds of the note
  """
  phoneme_pure = phoneme.replace('<word>', '').replace('</word>', '')
  
  if len(phoneme_pure) == 1:
    end = start + (0.5 * time_mult)
  elif len(phoneme_pure) == 2:
    end = start + (0.75 * time_mult)
  elif len(phoneme_pure) == 3:
    end = start + (1 * time_mult)
  elif len(phoneme_pure) == 4:
    end = start + (1.25 * time_mult)
  elif len(phoneme_pure) == 5:
    end = start + (1.5 * time_mult)
  elif len(phoneme_pure) == 6:
    end = start + (2 * time_mult)
  elif len(phoneme_pure) > 6:
    end = start + (2.25 * time_mult)

  return end

def final_pp(global_var, part_name):
  """
  This methods performs the final post production operations to the generated melody
  
  Parameters
  ----------
  global_var : dict
      The dictionary containing the global variables
  part_name : str
      The name of the current part
  """
  midi_list = []
  pitches_count = 0
  in_word_c = 0
  punctuation_offset = 0
  length_acc = 0

  pp_length = 0

  final_pp_settings = global_var['final_post_processing']
  part_time_mult = final_pp_settings[part_name]['time_mult']

  # update time multiplier based on if it is float or list
  if isinstance(part_time_mult, list):
    current_time_mult = part_time_mult[0]
  else:
    current_time_mult = part_time_mult

  # compute path of files
  base_path = os.path.join(global_var['auxiliary_temp_path'], part_name)

  txt_word_path = os.path.join(base_path, 'txt_word.txt')
  txt_punctuation_path = os.path.join(base_path, 'txt_punctuation.txt')
  melody_path = os.path.join(base_path, 'melody.mid')
  melody_pp_path = os.path.join(base_path, 'melody_pp.mid')

  # read phonemes file
  with open(txt_word_path, 'r') as o:
    phonemes = o.read()
  
  with open(txt_punctuation_path, 'r') as o:
    phonemes_p = o.read()

  phonemes_list = phonemes.strip().split()
  phonemes_p_list = phonemes_p.strip().split()

  # read midi file
  midi_data = pretty_midi.PrettyMIDI(melody_path)

  for instrument in midi_data.instruments:
    for note in instrument.notes:
      # get current note data
      start = note.start
      end = note.end
      pitch = note.pitch

      # get current phoneme
      phoneme = phonemes_list[pitches_count].replace('_', '')

      if pitches_count > 0:
        last_start = midi_list[pitches_count - 1][0]
        last_end = midi_list[pitches_count - 1][1]
        
        # always check that notes don't overlap, and if they do move them
        # or if legato mode is activate, legate the notes
        if start < last_end or final_pp_settings['add_legato']:
          start = last_end

        # apply pauses rules
        if start >= last_end:
          last_length = last_end - last_start
          length_acc += last_length

          # if long_note_short_pause rule is active and last note is longer than a threshold, apply randomly a legato or a small pause
          if final_pp_settings['long_note_short_pause_active'] == True and last_length >= final_pp_settings['long_note_short_pause_threshold']:
            start = last_end + random.choice(final_pp_settings['long_note_short_pause_time'])

          # if breathing_capacity rule is active and accumulated note is longer than a threshold, apply a small pause
          if final_pp_settings['breathing_capacity_active'] == True and length_acc >= final_pp_settings['breathing_capacity_threshold']:
            start = last_end + random.choice(final_pp_settings['breathing_capacity_pause'])
            length_acc = 0
          else:
            start = last_end

          # enforce two notes to be under an arbitrary number of seconds apart
          # this avoid too long pauses
          time_diff = start - last_end

          if time_diff > final_pp_settings['max_time_apart']:
            start = last_end + final_pp_settings['max_time_apart']
      
        # if the phoneme is part of a word, place it next to the end of previous note
        if in_word_c >= 1:
          start = last_end

      # check if punctuation, and if so add pause
      is_punctuation = phonemes_p_list[pitches_count + punctuation_offset] == '<punctuation>'

      if is_punctuation:
        start += random.choice(final_pp_settings['pause_between_punctuation'])
        punctuation_offset += 1

        # if time multiplier is a list, update index        
        if isinstance(part_time_mult, list):
          # if punctuation_offset >= len(part_time_mult):
          #   current_time_mult = part_time_mult[-1]
          # else:
          #   current_time_mult = part_time_mult[punctuation_offset]
          circular_index = (punctuation_offset) % len(part_time_mult)
          current_time_mult = part_time_mult[circular_index]
        else:
          current_time_mult = part_time_mult
        
        logging.info(f'Using time mult: {current_time_mult}')

      # adjust note ending based on phoneme length
      end = phoneme_to_length(phoneme, start, current_time_mult)
    
      # add to list
      midi_list.append([start, end, pitch])
      pitches_count += 1
      pp_length = end
      
      # check if word boundaries, and if so increase in word counter
      if '<word>' in phoneme:
        in_word_c += 1
      elif '</word>' in phoneme:
        in_word_c = 0

  logging.info(f'Wrote final post processed melody at {melody_pp_path}')
  write_midi_out(melody_pp_path, midi_list)

  return pp_length

def cut_extra(global_var, part_name):
  """
  This methods cuts the exceeding notes and lyrics to a maximum time defined
  in the global.yaml file
  
  Parameters
  ----------
  global_var : dict
      The dictionary containing the global variables
  part_name : str
      The name of the current part
  """
  min_time = global_var['melody_generation_parts'][part_name]['min_length']
  ideal_time = global_var['melody_generation_parts'][part_name]['ideal_length']
  max_time = global_var['melody_generation_parts'][part_name]['max_length']

  midi_list = []
  count = 0
  punctuation_offset = 0
  punctuation_index = []
  length_acc = 0

  total_final_length = 0
  stop_next = False

  # compute path of files
  base_path = os.path.join(global_var['auxiliary_temp_path'], part_name)
  
  lyrics_path = os.path.join(base_path, 'lyrics.txt')
  txt_path = os.path.join(base_path, 'txt.txt')
  txt_word_path = os.path.join(base_path, 'txt_word.txt')
  txt_punctuation_path = os.path.join(base_path, 'txt_punctuation.txt')
  melody_pp_path = os.path.join(base_path, 'melody_pp.mid')

  # read text files
  with open(lyrics_path, 'r') as o:
    lyrics = o.read()

  with open(txt_path, 'r') as o:
    phonemes = o.read()

  with open(txt_word_path, 'r') as o:
    phonemes_w = o.read()
  
  with open(txt_punctuation_path, 'r') as o:
    phonemes_p = o.read()

  lyrics_list = lyrics.strip().split('<punctuation>')
  phonemes_list = phonemes.strip().split()
  phonemes_w_list = phonemes_w.strip().split()
  phonemes_p_list = phonemes_p.strip().split()

  # read midi file
  midi_data = pretty_midi.PrettyMIDI(melody_pp_path)

  for instrument in midi_data.instruments:
    for note in instrument.notes:
      # get current note data
      start = note.start
      end = note.end
      pitch = note.pitch

      if end >= ideal_time:
        stop_next = True

      # get current phonemes
      phoneme = phonemes_list[count]
      phoneme_w = phonemes_w_list[count]

      # check if punctuation and if should stop
      phoneme_p = phonemes_p_list[count + punctuation_offset]
      is_punctuation = phoneme_p == '<punctuation>'

      if is_punctuation:
        punctuation_index.append(count)
        punctuation_offset += 1

        if stop_next:
          break

      # add to list
      midi_list.append([start, end, pitch])
      total_final_length = end
      count += 1
  
  # evaluate if it's better to take the last or the pre-last punctuation
  if len(punctuation_index) >= 2:
    prev_punctuation_idx = punctuation_index[-2] - 1
    prev_punctuation_end = midi_list[prev_punctuation_idx][1]

    last_punctuation_end = midi_list[-1][1]

    prev_distance = abs(ideal_time - prev_punctuation_end)
    last_distance = abs(ideal_time - last_punctuation_end)

    logging.info(f'prev end: {prev_punctuation_end} - last end: {last_punctuation_end}')
    logging.info(f'prev dist: {prev_distance} - last dist: {last_distance}')

    # if the pre-last item has a smaller distance than the last one,
    # set count and punctuation offset to cut lyrics
    # and cut midi and set final length
    if prev_distance < last_distance:
      count = prev_punctuation_idx + 1
      punctuation_offset = len(punctuation_index) - 1
      total_final_length = prev_punctuation_end

  punctuation_count = count + punctuation_offset

  # cut melody and lyrics
  midi_list = midi_list[:count]

  lyrics_cut = ' <punctuation>'.join(lyrics_list[:punctuation_offset]) + ' <punctuation>'
  phonemes_cut = ' '.join(phonemes_list[:count])
  phonemes_w_cut = ' '.join(phonemes_w_list[:count])
  phonemes_p_cut = ' '.join(phonemes_p_list[:punctuation_count])

  # make last note of melody longer
  midi_list[-1][1] += 1.

  # write cut text files
  base_path_out = os.path.join(global_var['out_path'], part_name)

  lyrics_path_out = os.path.join(base_path_out, 'lyrics.txt')
  txt_path_out = os.path.join(base_path_out, 'txt.txt')
  txt_word_path_out = os.path.join(base_path_out, 'txt_word.txt')
  txt_punctuation_path_out = os.path.join(base_path_out, 'txt_punctuation.txt')
  melody_pp_cut_path_out = os.path.join(base_path_out, 'melody_pp.mid')
  
  with open(lyrics_path_out, 'w') as o:
    o.write(lyrics_cut)

  with open(txt_path_out, 'w') as o:
    o.write(phonemes_cut)

  with open(txt_word_path_out, 'w') as o:
    o.write(phonemes_w_cut)
  
  with open(txt_punctuation_path_out, 'w') as o:
    o.write(phonemes_p_cut)
  
  # write cut midi
  write_midi_out(melody_pp_cut_path_out, midi_list)

  # log out
  logging.info(f'Wrote final cut post processed melody at {melody_pp_cut_path_out}')

  logging.info(f'Output text cut: {repr(lyrics_cut)}')
  logging.info(f'CSD text cut: {repr(phonemes_cut)}')
  logging.info(f'CSD text with word boundaries cut: {repr(phonemes_w_cut)}')
  logging.info(f'CSD text with punctuation cut: {repr(phonemes_p_cut)}')

  return total_final_length

# debug only
if __name__ == "__main__":
  with open('/content/Chasing_Waterfalls/global.yaml') as f: # load yaml
    global_var = yaml.load(f, Loader=SafeLoader)

  global_var['auxiliary_temp_path'] = '/content/Chasing_Waterfalls/out_files/2022-08-22_10-18-08/temp'
  global_var['out_path'] = '/content/Chasing_Waterfalls/out_files/2022-08-22_10-18-08'
  final_pp(global_var, 'part_C')
  cut_extra(global_var, 'part_C')