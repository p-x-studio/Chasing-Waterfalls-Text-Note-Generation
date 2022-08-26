"""
This script handles the melody generation based on chords using Music Transformer
"""
import logging
import time
import pretty_midi
from pathlib import Path
from midi_postprocessing import midi_postprocessing
from musicautobot.musicautobot.music_transformer.transform import *
from musicautobot.musicautobot.multitask_transformer.transform import *

def write_midi_out(midi_file_out, notes_list):
  """
  Given a list of notes, pitches start and end, it writes the corresponding midi file out

  Parameters
  ----------
  midi_file_out :  str
      The path to the midi file out 
  notes_list: list
      A list with three integers:
        - start note time
        - end note time
        - note pitch
  """
  out_midi = pretty_midi.PrettyMIDI()
  
  piano_program = pretty_midi.instrument_name_to_program('Acoustic grand piano')
  piano = pretty_midi.Instrument(program=piano_program)
  
  for note in notes_list:
    pretty_midi_note = pretty_midi.Note(velocity=127, pitch=note[2], start=note[0], end=note[1])
    piano.notes.append(pretty_midi_note)

  out_midi.instruments.append(piano)
  out_midi.write(midi_file_out)

def merge_midi(merge_list, out_midi_path, quantize_end_times):
  """
  Merge a list of midi file into a single one, by concatenating the individual
  midi files

  Parameters
  ----------
  merge_list : list -> (str, int)
      A dictionary cointaining for every part a list with:
        - path of midi files to merge 
        - corresponding bars number of the midi file
  out_midi_path : str
      Path to the output merged midi file
  quantize_end_times : bool
      If true, it quantizes the end time to the number of bar specified on global.yaml file
      If false, uses the Music Transformer predicted end time
  Returns
  -------
  int
      The number of pitches in the generated merged melody
  """
  midi_list = []
  pitches_count = 0
  part_offset = 0

  for midi, bars in merge_list:
    # read midi file
    midi_data = pretty_midi.PrettyMIDI(midi)
    quantized_bars = bars * 2

    for instrument in midi_data.instruments:
      for note in instrument.notes:
        start = note.start + part_offset
        end = note.end + part_offset
        pitch = note.pitch
        midi_list.append([start, end, pitch])

        pitches_count += 1

    midi_end_time = midi_data.get_end_time()

    if quantize_end_times:
      part_offset += quantized_bars # round the midi end time in order to keep quantization
    else:
      part_offset += midi_end_time

    logging.info(f"Merging midi: {midi} - End time: {midi_end_time} (q: {quantized_bars}) - Part offset: {part_offset} - Quantized: {quantize_end_times}")
  
  # write merged midi file out
  write_midi_out(out_midi_path, midi_list)
  logging.info(f'Wrote merged .mid to: {out_midi_path}')

  return pitches_count

def generate_melody_part(learner,
                         chords,
                         melody_seed,
                         out_midi_part_raw_path,
                         out_midi_part_pp_path,
                         part,
                         global_var):
  """
  Generates the a subpart of the melody conditioned to a chord, and applies 
  post-processing to it

  Parameters
  ----------
  learner :  MultitaskLearner
      The Music Transformer learner instance 
  data: MusicDataBunch
      The data of the Music Transformer learner instance 
  out_midi_part_raw_path:
      Path to the raw midi out directly from the music transformer model
  out_midi_part_pp_path:
      Path to the midi post processed with the midi_postprocessing function
  part:
      Part of the melody, as specified in global.yaml
  global_var : dict
      The dictionary containing the global variables 

  Returns
  -------
  music21.MusicItem
      The genenerated melody from the music transformer
  """
  pred_melody, generated_words = learner.predict_s2s_whole_chords(chords, 
                                                                  melody_seed, 
                                                                  use_memory=True, 
                                                                  temperatures=(part['pitch_temp'], part['tempo_temp']), 
                                                                  top_k=part['top_k'],
                                                                  top_p=part['top_p'])
  pred_melody.stream.write('midi', out_midi_part_raw_path)

  # Post process melody
  midi_postprocessing(
    out_midi_part_raw_path,
    out_midi_part_pp_path,
    part['seed'], 
    global_var,
    part['time_multiplier'],
    part['poly_to_mono_logic'],
    part['add_legato'])
  
  return pred_melody

def generate_melody(learner, data, global_var, part_name):
  """
  Generates the melody conditioned to chords using Music Transformer
  It generates many melodies conditioned on different chords, and merge them
  together to have the final melody

  Parameters
  ----------
  learner :  MultitaskLearner
      The Music Transformer learner instance 
  data: MusicDataBunch
      The data of the Music Transformer learner instance 
  global_var : dict
      The dictionary containing the global variables 
  part_name : str
      The name of the current macro-part

  Returns
  -------
  int
      The number of pitches in the generated merged melody
  """
  auxiliary_temp_path = os.path.join(global_var['auxiliary_temp_path'], part_name)
  part = global_var['melody_generation_parts'][part_name]

  # Constants
  rep_number = 5

  # Generate individual melody micro-parts
  merge_list = []
  chords_file_name = Path(part['chords']).stem

  logging.info(f'Currently working on: {chords_file_name}.mid')

  # Encode input chords and melody seed
  chords = MusicItem.from_file(part['chords'], data.vocab)
  melody_seed = MusicItem.from_file(part['seed'], data.vocab)

  # Generate melodies
  for i in range(0, rep_number):
    logging.info(f'Currently working on repetition number: {i}')
    out_midi_part_raw_path = os.path.join(auxiliary_temp_path, f'{chords_file_name}_raw_{i}.mid')
    out_midi_part_pp_path = os.path.join(auxiliary_temp_path, f'{chords_file_name}_pp_{i}.mid')

    first_melody = generate_melody_part(learner,
                                        chords,
                                        melody_seed,
                                        out_midi_part_raw_path,
                                        out_midi_part_pp_path,
                                        part,
                                        global_var)
    
    # create merge list item by toupling the post processed midi path, 
    # with his corresponding bars number
    
    merge_list_touple = (out_midi_part_pp_path, part['chords_n_bars'])
    merge_list.append(merge_list_touple)
  
  # Merge parts in a single midi file
  out_midi_final_path = os.path.join(auxiliary_temp_path, f'melody_{part_name}_no_ending.mid')
  pitches_count = merge_midi(merge_list, 
                             out_midi_final_path, 
                             global_var['quantize_end_times'])
  
  return pitches_count

def generate_ending_melody(missing_notes, learner, data, global_var, part_name):
  """
  Generates the last bit of the melody by cutting it according to the missing_notes parameter,
  and then merges it to the main melody generated earlier

  Parameters
  ----------
  missing_notes : int
      The number of missing notes to be generated
  learner :  MultitaskLearner
      The Music Transformer learner instance 
  data: MusicDataBunch
      The data of the Music Transformer learner instance 
  global_var : dict
      The dictionary containing the global variables 
  part_name : str
      The name of the current macro-part

  Returns
  -------
  int
      The number of pitches in the generated merged melody
  """
  out_path = os.path.join(global_var['out_path'], part_name)
  auxiliary_temp_path = os.path.join(global_var['auxiliary_temp_path'], part_name)
  melody_ending_data = global_var['melody_ending_parts'][part_name]

  chords_file_name = Path(melody_ending_data['chords']).stem
  logging.info(f'Currently working on ending with chords: {chords_file_name}.mid')

  # Encode input chords and melody seed
  chords = MusicItem.from_file(melody_ending_data['chords'], data.vocab)
  melody_seed = MusicItem.from_file(melody_ending_data['seed'], data.vocab)

  # Generate melody
  out_midi_ending_raw_path = os.path.join(auxiliary_temp_path, f'ending_raw.mid')
  out_midi_ending_pp_path = os.path.join(auxiliary_temp_path, f'ending_pp.mid')

  ending_melody = generate_melody_part(learner,
                                       chords,
                                       melody_seed,
                                       out_midi_ending_raw_path,
                                       out_midi_ending_pp_path,
                                       melody_ending_data,
                                       global_var)

  # Cut ending melody to right number of missing notes
  cut_midi_list = [] 
  pitches_count = 0

  # Cut ending melody
  midi_data = pretty_midi.PrettyMIDI(out_midi_ending_pp_path)

  for instrument in midi_data.instruments:
    for note in instrument.notes:
      start = note.start
      end = note.end
      pitch = note.pitch
      cut_midi_list.append([start, end, pitch])

      pitches_count += 1

      # if all the notes needed are computed, ignore the rest
      if (pitches_count >= missing_notes):
        break
  
  # write cut midi file out
  ending_melody_path = os.path.join(auxiliary_temp_path, f'ending_pp_cut.mid')
  write_midi_out(ending_melody_path, cut_midi_list)

  logging.info(f'Wrote cutted ending melody at {pitches_count} pitches')

  # Merge main melody with ending melody
  main_melody_path = os.path.join(auxiliary_temp_path, f'melody_{part_name}_no_ending.mid')
  out_midi_final_path = os.path.join(auxiliary_temp_path, 'melody.mid')

  merge_list = [
    (main_melody_path, -1),
    (ending_melody_path, -1)
  ]

  final_pitches_count = merge_midi(merge_list, 
                                   out_midi_final_path, 
                                   False)
  
  return final_pitches_count