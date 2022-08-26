"""
This script handles the melody and text generation pipeline
"""
import math
import openai
import urllib.request
import logging
import os
import shutil
import datetime
import yaml

from yaml.loader import SafeLoader

from musicautobot.musicautobot.numpy_encode import *
from musicautobot.musicautobot.config import *
from musicautobot.musicautobot.music_transformer import *
from musicautobot.musicautobot.multitask_transformer import *

from melody_generation import *
from text_generation import *
from final_postprocessing import *

def setup(yaml_path = 'global.yaml'):
  """
  Run the setup operation:
    - loads the yaml file with global variables
    - computes a unique run ID
    - creates folder structure
    - define logging format

  Parameters
  ----------
  yaml_path : str (optional, default: global.yaml)
      Path to the yaml file with the global variables
  
  Returns
  -------
  dict
      A dictionary with all the global variables set
  """
  with open(yaml_path) as f: # load yaml
    global_var = yaml.load(f, Loader=SafeLoader)

  # create run path
  run_id = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
  out_path = Path(os.path.join(global_var['base_out_path'], run_id))
  out_path.mkdir(parents=True, exist_ok=True)
  
  # add auxiliary folders
  auxiliary_temp_path = Path(os.path.join(out_path, "temp"))
  auxiliary_temp_path.mkdir(parents=True, exist_ok=True)

  # set openai API key
  openai.api_key = global_var['openai_api_key']

  # define logging settings
  logging.basicConfig(
    format='%(asctime)s %(levelname)-8s [%(filename)s:%(lineno)s - %(funcName)s()] %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S')

  # add run-time generated global var
  global_var['out_path'] = out_path
  global_var['auxiliary_temp_path'] = auxiliary_temp_path
  global_var['run_id'] = run_id

  return global_var

def create_learner_instance(saved_daset_path = 'data/numpy'):
  """
  Downloads pre-trained model and creates the Music Transformer learner model instance 

  Parameters
  ----------
  saved_daset_path : str (optional, default: data/numpy)
      Path to the saved dataset
  
  Returns
  -------
  (MultitaskLearner, MusicDataBunch)
      A tuple with the learner instance and the data loaded
  """
  config = multitask_config()

  # Create data instance from saved dataset
  data_path = Path(saved_daset_path)
  data_save_name = 'musicitem_data_save.pkl'
  data = MusicDataBunch.empty(data_path)

  logging.info('Downloading pretrained model')
  # Download pretrained model
  pretrained_url = 'https://ashaw-midi-web-server.s3-us-west-2.amazonaws.com/pretrained/MultitaskSmallKeyC.pth'

  pretrained_path = data_path/'pretrained'/Path(pretrained_url).name
  pretrained_path.parent.mkdir(parents=True, exist_ok=True)
  if not os.path.exists(pretrained_path):
    urllib.request.urlretrieve(pretrained_url, pretrained_path)

  # Learner
  logging.info('Creating learner')
  learner = multitask_model_learner(data, pretrained_path=pretrained_path)

  return learner, data

def main():
  """
  Runs the melody and text generation pipeline
  """
  global_var = setup()

  logging.info(f'Run ID: {global_var["run_id"]}')
  logging.info('Setting up model')
  learner, data = create_learner_instance()

  prompt_append = '' 
  part_count = 0

  for part_name, part_data in global_var['melody_generation_parts'].items():
    part_completed = False

    while part_completed == False:
      logging.info(f'Working on part: {part_name}')

      # create directory structure for macro-part
      temp_path = Path(os.path.join(global_var['auxiliary_temp_path'], part_name))
      temp_path.mkdir(parents=True, exist_ok=True)

      out_path = Path(os.path.join(global_var['out_path'], part_name))
      out_path.mkdir(parents=True, exist_ok=True)

      # generate melody
      logging.info(f'Generating melody')
      pitches_count = generate_melody(learner, data, global_var, part_name)

      # generate text
      for i in range(0, 10):
        logging.info(f'Generating text - Trial {i+1}')

        # if story coherence is activate, not include prompt in parts after the first one
        if part_count > 0 and global_var['story_coherence_between_parts'] == True:
          include_prompt = False
        else:
          include_prompt = global_var['gpt3_include_seed']

        logging.info(f'Include prompt: {include_prompt}')
        

        output_text, csd_text, csd_text_punctuation, csd_text_word = generate_text(pitches_count, 
                                                                                   global_var,
                                                                                   part_name,
                                                                                   prompt_append=prompt_append,
                                                                                   include_prompt_text=include_prompt,
                                                                                   frequency_penalty = 1.5,
                                                                                   presence_penalty = 1.5,
                                                                                   temperature = 0.9)
        # if phonemization was unsuccesfull, try again
        if output_text == 0 and csd_text == 0 and csd_text_punctuation == 0 and csd_text_word == 0:
          part_completed = False
          continue
        else:
          # check if GPT3 didn't exceed the max number of requests set
          if output_text != -1 and csd_text != -1 and csd_text_punctuation != -1 and csd_text_word != -1:
            syllables_count = len(csd_text.split(" "))

            logging.info(f'Output text: {repr(output_text)}')
            logging.info(f'CSD text: {repr(csd_text)}')
            logging.info(f'CSD text with punctuation: {repr(csd_text_punctuation)}')
            logging.info(f'CSD text with word boundaries: {repr(csd_text_word)}')
            logging.info(f'Syllables count: {syllables_count}')
            logging.info(f'Pitches count: {pitches_count}')

            missing_notes = syllables_count - pitches_count
            logging.info(f'Missing notes: {missing_notes}')

            # if needed, create ending phrase of melody and text
            if syllables_count > pitches_count:
              pitches_count = generate_ending_melody(missing_notes, learner, data, global_var, part_name)
              logging.info(f'Final pitches count: {pitches_count}')
            else: # copy the melody from the temp folder to the main one
              temp_melody_path = os.path.join(temp_path, f'melody_{part_name}_no_ending.mid')
              main_melody_path = out_midi_final_path = os.path.join(temp_path, 'melody.mid')
              
              shutil.copy(temp_melody_path, main_melody_path)

            # apply final post processing
            pp_length = final_pp(global_var, part_name)
            # cut extra note and lyrics
            total_final_length = cut_extra(global_var, part_name)
            logging.info(f'Total final length: {total_final_length}')

            # evaluate if length is within range, otherwise restart
            min_time = global_var['melody_generation_parts'][part_name]['min_length']
            max_time = global_var['melody_generation_parts'][part_name]['max_length']

            if total_final_length < min_time or total_final_length > max_time:
              logging.info('Total final length not in range. Restart part.')
              part_completed = False
            else:
              part_completed = True
              part_count += 1

            # give continuity to the GPT3 text generation between parts
            if global_var['story_coherence_between_parts'] and part_completed:
              prompt_append = output_text.replace('<punctuation>', '.')
          else:
            logging.error('Critical error - max GPT3 requests exceeded')
          
        break

main()