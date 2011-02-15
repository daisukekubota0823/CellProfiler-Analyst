#!/usr/bin/env python

from singleton import Singleton
from StringIO import StringIO
import re
import os
import logging
import incell

#
# THESE MUST INCLUDE DEPRECATED FIELDS (shown side-by-side)
#

string_vars = ['db_type', 
               'db_port', 
               'db_host', 
               'db_name', 
               'db_user', 
               'db_passwd',
               'image_table', 
               'object_table',
               'image_csv_file', 
               'object_csv_file',
               'table_id', 
               'image_id', 
               'object_id', 
               'plate_id', 
               'well_id',
               'cell_x_loc', 
               'cell_y_loc',
               'image_url_prepend',
               'image_tile_size', 
               'image_buffer_size',
               'tile_buffer_size',
               'area_scoring_column',
               'training_set',
               'class_table',
               'plate_type',
               'check_tables',
               'db_sql_file',
               'db_sqlite_file',
               'use_larger_image_scale', 
               'rescale_object_coords',
               'well_format',
               'link_tables_table',
               'link_columns_table',
               'image_rescale',
               ]

list_vars = ['image_path_cols', 'image_channel_paths', 
             'image_file_cols', 'image_channel_files', 
             'image_names', 'image_channel_names', 
             'image_channel_colors', 
             'channels_per_image', 
             'image_channel_blend_modes', 
             'object_name',
             'classifier_ignore_substrings', 
             'classifier_ignore_columns',
             'image_thumbnail_cols']

optional_vars = ['db_port', 
                 'db_host', 
                 'db_name', 
                 'db_user', 
                 'db_passwd',
                 'table_id', 
                 'image_url_prepend', 
                 'image_csv_file',
                 'image_channel_names', 'image_names', 
                 'image_channel_colors',
                 'channels_per_image', 
                 'image_channel_blend_modes',
                 'object_csv_file', 
                 'area_scoring_column', 
                 'training_set',
                 'class_table',
                 'image_buffer_size', 
                 'tile_buffer_size',
                 'plate_id', 
                 'well_id', 
                 'plate_type',
                 'classifier_ignore_substrings', 'classifier_ignore_columns',
                 'object_name',
                 'check_tables',
                 'db_sql_file',
                 'db_sqlite_file',
                 'object_table', 
                 'object_id',
                 'cell_x_loc', 
                 'cell_y_loc',
                 'use_larger_image_scale', 
                 'rescale_object_coords',
                 'image_thumbnail_cols',
                 'well_format',
                 'link_tables_table',
                 'link_columns_table',
                 'image_rescale',
                 ]

# map deprecated fields to new fields
field_mappings = {'classifier_ignore_substrings' : 'classifier_ignore_columns',
                  'image_channel_files' : 'image_file_cols',
                  'image_channel_paths' : 'image_path_cols',
                  'image_channel_names' : 'image_names',
                  }

required_vars = list(set(list_vars + string_vars) - set(optional_vars) 
                     - set(field_mappings.keys()))

valid_vars = set(list_vars + string_vars)

class Properties(Singleton):
    '''
    Loads and stores properties files.
    '''
    def __init__(self):
        super(Properties, self).__init__()        
        self._groups = {}
        self._groups_ordered = []
        self._filters = {}
        self._filters_ordered = []
        self._initialized = False
    
    def __str__(self):
        s=''
        for k, v in sorted(self.__dict__.items()):
            if not str(k).startswith('_'):
                s += k+" = "+str(v)+"\n"
        return s
        
    def __getattr__(self, field):
        # The name may not be loaded for optional fields.
        if (not self.__dict__.has_key(field)) and (field in valid_vars):
            return None
        else:
            return self.__dict__[field]
        
    def __setattr__(self, id, val):
        self.__dict__[id] = val
    
    def show_load_dialog(self):
        import wx
        if not wx.GetApp():
            raise Exception("Can't display load dialog without a wx App.")
        dlg = wx.FileDialog(None, "Select a the file containing your properties.", style=wx.OPEN|wx.FD_CHANGE_DIR)
        if dlg.ShowModal() == wx.ID_OK:
            filename = dlg.GetPath()
            os.chdir(os.path.split(filename)[0])  # wx.FD_CHANGE_DIR doesn't seem to work in the FileDialog, so I do it explicitly
            self.LoadFile(filename)
            return True
        else:
            return False
        
    def parse_list_value(self, list_str):
        '''parses a list property given as a string and returns it as a list
        '''
        return [v.strip() for v in list_str.split(',') if v.strip() is not '']
        
    def load_file(self, filename):
        ''' Loads variables in from a properties file. '''
        self.clear()
        self._groups = {}
        self._groups_ordered = []
        self._filters = {}
        self._filters_ordered = []
        self._filename = filename

        f = open(filename, 'U')        
        lines = f.read()
        self._textfile = lines
        # replace CRs with LFs
        #lines = lines.replace('\r', '\n')
        lines = lines.split('\n')

        for idx in xrange(len(lines)):
            line = lines[idx]
            # skip commented and empty lines
            if not line.strip().startswith('#') and line.strip() != '':
                try:
                    (name, val) = line.split('=', 1)
                    name = name.strip()
                    val = val.strip()
                except ValueError:
                    raise Exception('PROPERTIES ERROR: Could not parse line #%d\n'
                                    '\t"%s"\n'
                                    'Did you accidentally load your training set instead of your properties file?'%(idx + 1, line))
                
                if name in string_vars:
                    self.__dict__[name] = val or None
                
                elif name in list_vars:
                    self.__dict__[name] = self.parse_list_value(val) or None
                    
                elif name.startswith('group_SQL_'):
                    group_name = name[10:]
                    if group_name == '':
                        raise Exception, ('PROPERTIES ERROR (%s): "group_SQL_" should be followed by a group name.\n'
                                          'Example: "group_SQL_MyGroup = <QUERY>" would define a group named "MyGroup" defined by\n'
                                          'a MySQL query "<QUERY>". See the README.'%(name))
                    if group_name in self._groups.keys():
                        raise Exception, 'Group "%s" is defined twice in properties file.'%(group_name)
                    if group_name in self._filters.keys():
                        raise Exception, 'Name "%s" is already taken for a filter.'%(group_name)
                    if not val:
                        logging.warn('PROPERTIES WARNING (%s): Undefined group'%(name))
                        continue
                    # TODO: test query
                    self._groups[group_name] = val
                    self._groups_ordered += [group_name]
                    
                elif name.startswith('filter_SQL_'):
                    # Handle old-style filters:
                    filter_name = name[11:]
                    if filter_name == '':
                        raise Exception, ('PROPERTIES ERROR (%s): "filter_SQL_" should be followed by a filter name.\n'
                                          'Example: "filter_SQL_MyFilter = <QUERY>" would define a filter named "MyFilter" defined by\n'
                                          'a MySQL query "<QUERY>". See the README.'%(name))
                    if filter_name in self._filters.keys():
                        raise Exception, 'Filter "%s" is defined twice in properties file.'%(filter_name)
                    if filter_name in self._groups.keys():
                        raise Exception, 'Name "%s" is already taken for a group.'%(filter_name)
                    if re.search('\W', filter_name):
                        raise Exception, 'PROPERTIES ERROR (%s): Filter names may only contain alphanumeric characters and "_".'%(filter_name)
                    if not val:
                        logging.warn('PROPERTIES WARNING (%s): Undefined filter'%(name))
                        continue
                    import sqltools
                    self._filters[filter_name] = sqltools.OldFilter(filter_name, val)
                    self._filters_ordered += [filter_name]
                
                elif name in ['groups', 'filters']:
                    logging.warn('PROPERTIES WARNING (%s): This field is no longer necessary in the properties file.\n'
                              'Only the group_SQL_XXX and filter_SQL_XXX fields are needed when defining groups and filters.'%(name))
                    
                #elif name == 'gates':
                    ## gates are the new filters
                    ## gates are all the rage
                    ## gates are the new black
                    #not_parsed = True
                    #gates = ''
                    #while not_parsed:
                        #gates += val.strip()
                        #try:
                            #self.__dict__[name] = eval(gates)
                            #not_parsed = False
                        #except SyntaxError:
                            #idx += 1
                            #if idx >= len(lines):
                                #raise Exception, 'PROPERTIES ERROR: Error parsing gates. Could not find end of definition.'
                            #val = lines[idx]
                    
                else:
                    logging.warn('PROPERTIES WARNING: Unrecognized field "%s" in properties file'%(name))
                
        f.close()
        self.Validate()
        self._initialized = True
    LoadFile = load_file

    def LoadIncellFiles(self, properties_filename, sqlite_filename, incell_filenames):
        if os.path.exists(properties_filename):
            self.LoadFile(properties_filename)
        else:
            self._filename = properties_filename
            self._textfile = ""

        for incell_filename in incell_filenames:
            incell.parse_incell(sqlite_filename, incell_filename, self)
            self.Validate()
        self._initialized = True

        if not os.path.exists(properties_filename):
            self.SaveFile(properties_filename)
        
    def save_file(self, filename):
        '''
        Saves the file including original comments and whitespace. 
        This function skips vars that start with _ (underscore)
        '''
        f = open(filename, 'w')
        self._filename = filename
        
        fields_to_write = set([k for k in self.__dict__.keys() if not k.startswith('_')])
        
        # Write whole file out replacing any changed values
        for line in StringIO(self._textfile):
            if line.strip().startswith('#') or line.strip()=='':
                f.write(line)
            else:
                (name, oldval) = line.split('=', 1)    # split each side of the first eq sign
                name = name.strip()
                oldval = oldval.strip()
                val = self.__getattr__(name)
                if name in string_vars and str(val) == oldval:
                    # write string fields back if they're the same
                    f.write(line)
                elif name in list_vars and val == parse_list_value(oldval):
                    # write list vars back if they're the same
                    f.write(line)
                elif name.startswith('group') or name.startswith('filter'):
                    # write old groups and filters back as they were
                    f.write(line)
                else:
                    # the field value has changed
                    if type(val)==list:
                        f.write('%s  =  %s\n'%(name, ', '.join([str(v) for v in val if v])))
                    else:
                        f.write('%s  =  %s\n'%(name, val))
                fields_to_write.remove(name)
        
        f.write('\n')
        # Write out fields that weren't present in the file
        for field in fields_to_write:
            val = self.__getattr__(field)
            if type(val)==list:
                f.write('%s  =  %s\n'%(field, ', '.join([str(v) for v in val if v])))
            else:
                f.write('%s  =  %s\n'%(field, val))
        
        f.close()
        
    def clear(self):
        # only clear known variables
        for k in valid_vars & set(self.__dict__.keys()):
            del self.__dict__[k]
        self._groups = {}
        self._groups_ordered = []
        self._filters = {}
        self._filters_ordered = []
        self._initialized = True
        
    def is_initialized(self):
        return self._initialized

    def field_defined(self, name):
        # field name exists and has a non-empty value.
        return self.__dict__.get(name, None) not in ['', None]
    
    def backwards_compatiblize(self):
        ''' Update any old fields to new ones in field_mappings.
        '''
        for old, new in field_mappings.items():
            if self.field_defined(old):
                logging.warn('PROPERTIES WARNING (%s): This field name has been '
                          'deprecated, use "%s" instead.'%(old, new)) 
                if not self.field_defined(new):
                    self.__dict__[new] = self.__dict__[old]
                else:
                    raise Exception, ('PROPERTIES ERROR: Both "%s" and "%s" were '
                        'found in your properties file. The field "%s" has been '
                        'deprecated and renamed to "%s". Please remove "%s" from '
                        'your properties file.'%(old, new, old, new, old))
                del self.__dict__[old]

    def Validate(self):
        '''Checks the validity of each field and their values.
        '''
        # update old fields
        self.backwards_compatiblize()
        
        # check that all required fields are defined
        for name in required_vars:
            assert self.field_defined(name), 'PROPERTIES ERROR (%s): Field is missing or empty.'%(name)
        
        assert self.db_type.lower() in ['mysql', 'sqlite'], 'PROPERTIES ERROR (db_type): Value must be either "mysql" or "sqlite".'
        
        # BELOW: Check sometimes-optional fields, and print warnings etc
        if self.db_type.lower()=='sqlite':
            for field in ['db_port', 'db_host', 'db_name', 'db_user', 'db_passwd',]:
                if self.field_defined(field):
                    logging.warn('PROPERTIES WARNING (%s): Field not required with db_type=sqlite.'%(field))
            
            assert any([self.field_defined(field) for field in ['image_csv_file','object_csv_file','db_sql_file','db_sqlite_file']]), \
                    'PROPERTIES ERROR: When using db_type=sqlite, you must also supply the fields "image_csv_file" and "object_csv_file" OR "db_sql_file" OR "db_sqlite_file". See the README.'
            
            if self.field_defined('db_sqlite_file'):
                if not os.path.isabs(self.db_sqlite_file):
                    # Make relative paths relative to the props file location
                    # TODO: This sholdn't be permanent
                    self.db_sqlite_file = os.path.join(os.path.dirname(self._filename), self.db_sqlite_file)                
                try:
                    f = open(self.db_sqlite_file, 'r')
                    f.close()
                except:
                    raise Exception, 'PROPERTIES ERROR (%s): SQLite database could not be found at "%s".'%('db_sqlite_file', self.db_sqlite_file)
            
            if self.field_defined('db_sql_file'):
                if not os.path.isabs(self.db_sql_file):
                    # Make relative paths relative to the props file location
                    # TODO: This sholdn't be permanent
                    self.db_sql_file = os.path.join(os.path.dirname(self._filename), self.db_sql_file)
                try:
                    f = open(self.db_sql_file, 'r')
                    f.close()
                except:
                    raise Exception, 'PROPERTIES ERROR (%s): File "%s" could not be found.'%('db_sql_file', self.db_sql_file)
                
                for field in ['image_csv_file','object_csv_file']:
                    assert not self.field_defined(field), 'PROPERTIES ERROR (%s, db_sql_file): Both of these fields cannot be used at the same time.'%(field)
            else:        
                for field in ['image_csv_file','object_csv_file']:
                    if self.field_defined(field):
                        if not os.path.isabs(self.__dict__[field]):
                            # Make relative paths relative to the props file location
                            # TODO: This sholdn't be permanent
                            self.__dict__[field] = os.path.join(os.path.dirname(self._filename), self.__dict__[field])

                        try:
                            f = open(self.__dict__[field], 'r')
                            f.close()
                        except:
                            raise Exception, 'PROPERTIES ERROR (%s): File "%s" could not be found.'%(field, self.__dict__[field])                
            
        if self.db_type.lower()=='mysql':
            for field in ['db_host', 'db_name', 'db_user',]:
                assert self.field_defined(field), 'PROPERTIES ERROR (%s): Field is required with db_type=mysql.'%(field)
            if not self.field_defined('db_port'):
                self.db_port = '3306'
                logging.info('PROPERTIES: Using default db_port=3306 for MySQL.')
            for field in ['image_csv_file','object_csv_file']:
                if self.field_defined(field):
                    logging.warn('PROPERTIES WARNING (%s): Field not required with db_type=mysql.'%(field))
        
        if self.field_defined('area_scoring_column'):
            logging.info('PROPERTIES: Area scoring will be used.')
                
        if not self.field_defined('image_channel_colors'):
            logging.warn('PROPERTIES WARNING (image_channel_colors): No value(s) specified. CPA will use a generic channel-color mapping.')
            self.image_channel_colors = ['red', 'green', 'blue']+['none' for x in range(97)]
        
        if not self.field_defined('channels_per_image'):
            logging.warn('PROPERTIES WARNING (channels_per_image): No value(s) specified. CPA will assume 1 channel per image.')
            self.channels_per_image = ['1' for i in range(len(self.image_file_cols))]

        if not self.field_defined('image_names'):
            logging.warn('PROPERTIES WARNING (image_names): No value(s) specified. CPA will use generic channel names.')
            self.image_names = ['channel-%d'%(i+1) for i in range(len(self.image_file_cols))]

        if len(self.image_channel_colors) < sum(map(int, self.channels_per_image)):
            self.image_channel_colors = ['red', 'green', 'blue']
            self.image_channel_colors += ['none' for x in range(min(sum(map(int, self.channels_per_image)) - 3, 0))]
            logging.warn('PROPERTIES WARNING (image_channel_colors): You did not '
                      'specify enough colors for all the channels in your images. '
                      'One color should be listed for each file column listed in '
                      'image_file_cols unless your images contain multiple '
                      'channels, in which case you need one for the sum of all '
                      'the channels specified by "channels_per_image". CPA, will '
                      'use channel colors %s for this run.'%(self.image_channel_colors,))

        assert len(self.image_file_cols) == len(self.image_path_cols), \
               'PROPERTIES ERROR: image_file_cols and image_path_cols must have an equal number of values.'
        
        assert len(self.image_file_cols) == len(self.channels_per_image), \
               'PROPERTIES ERROR: channels_per_image must have the same number of values as image_file_cols  and image_path_cols.'

        assert len(self.image_file_cols) == len(self.image_names), \
               'PROPERTIES ERROR: image_names must have the same number of values as image_file_cols  and image_path_cols.'
                    
        if self.field_defined('image_channel_blend_modes'):
            for mode in self.image_channel_blend_modes:
                assert mode in ['add', 'subtract', 'solid'], 'PROPERTIES ERROR (image_channel_blend_modes): Blend modes must list of modes (1 for each image channel). Valid modes are add, subtract and solid.'
            
        if not self.field_defined('classifier_ignore_columns'):
            logging.warn('PROPERTIES WARNING (classifier_ignore_columns): No value(s) specified. Classifier will use ALL NUMERIC per_object columns when training.')
        
        if not self.field_defined('image_buffer_size'):
            logging.info('PROPERTIES: Using default image_buffer_size=1')
            self.image_buffer_size = '1'
            
        if not self.field_defined('tile_buffer_size'):
            logging.info('PROPERTIES: Using default tile_buffer_size=1')
            self.tile_buffer_size = '1'
            
        if not self.field_defined('object_name'):
            logging.warn('PROPERTIES WARNING (object_name): No object name specified, will use default: "object_name=cell,cells"')
            self.object_name = ['cell', 'cells']
        else:
            # if it is defined make sure they do it correctly
            assert len(self.object_name)==2, 'PROPERTIES ERROR (object_name): Found %d names instead of 2! This field should contain the singular and plural name of the objects you are classifying. (Example: object_name=cell,cells)'%(len(self.object_name))

        if self.field_defined('training_set'):
            if not os.path.isabs(self.training_set):
                # Make relative paths relative to the props file location
                # TODO: This sholdn't be permanent
                self.training_set = os.path.join(os.path.dirname(self._filename), self.training_set)
            try:
                f = open(self.training_set)
                f.close()
            except:
                logging.warn('PROPERTIES WARNING (training_set): Training set at "%s" could not be found.'%(self.training_set))
            logging.info('PROPERTIES: Training set found at "%s"'%(self.training_set))
        
        if self.field_defined('class_table'):
            assert self.class_table != self.image_table, 'PROPERTIES ERROR (class_table): class_table cannot be the same as image_table!'
            assert self.class_table != self.object_table, 'PROPERTIES ERROR (class_table): class_table cannot be the same as object_table!'
            logging.info('PROPERTIES: Per-Object classes will be written to table "%s"'%(self.class_table))
            
        if not self.field_defined('plate_id'):
            logging.warn('PROPERTIES WARNING (plate_id): Field is required for plate map viewer.')
                                    
        if not self.field_defined('well_id'):
            logging.warn('PROPERTIES WARNING (well_id): Field is required for plate map viewer.')
                                    
        if not self.field_defined('plate_type'):
            logging.warn('PROPERTIES WARNING (plate_type): Field is required for plate map viewer.')
            
        if self.field_defined('check_tables') and self.check_tables.lower() in ['false', 'no', 'off', 'f', 'n']:
            self.check_tables = 'no'
        elif not self.field_defined('check_tables') or self.check_tables.lower() in ['true', 'yes', 'on', 't', 'y']:
            self.check_tables = 'yes'
        else:
            logging.warn('PROPERTIES WARNING (check_tables): Field value "%s" is invalid. Replacing with "yes".'%(self.check_tables))
            self.check_tables = 'yes'
            
        if self.use_larger_image_scale in [True, False]:
            pass
        elif not self.field_defined('use_larger_image_scale') or self.use_larger_image_scale.lower() in ['false', 'no', 'off', 'f', 'n']:
            self.use_larger_image_scale = False
        elif self.field_defined('use_larger_image_scale') and self.use_larger_image_scale.lower() in ['true', 'yes', 'on', 't', 'y']:
            self.use_larger_image_scale = True
        else:
            logging.warn('PROPERTIES WARNING (use_larger_image_scale): Field value "%s" is invalid. Replacing with "false".'%(self.use_larger_image_scale))
            self.use_larger_image_scale = False
            
        if self.rescale_object_coords in [True, False]:
            pass
        elif not self.field_defined('rescale_object_coords') or self.rescale_object_coords.lower() in ['false', 'no', 'off', 'f', 'n']:
            self.rescale_object_coords = False
        elif self.field_defined('rescale_object_coords') and self.rescale_object_coords.lower() in ['true', 'yes', 'on', 't', 'y']:
            self.rescale_object_coords = True
        else:
            logging.warn('PROPERTIES WARNING (rescale_object_coords): Field value "%s" is invalid. Replacing with "false".'%(self.rescale_object_coords))
            self.rescale_object_coords = False
            
        if not self.field_defined('well_format'):
            self.well_format = 'A01'
            logging.warn('PROPERTIES WARNING (well_format): Field was not defined, using default format of "A01".')
            
        if not self.field_defined('link_tables_table'):
            self.link_tables_table = '_link_tables_%s_'%(self.image_table)
            
        if not self.field_defined('link_columns_table'):
            self.link_columns_table = '_link_columns_%s_'%(self.image_table)
        

if __name__ == "__main__":
    import sys
    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
    
    p = Properties.getInstance()
    if len(sys.argv) >= 2:
        filename = sys.argv[1]
    else:
        #filename = "../properties/nirht_test.properties"
        filename = '/Users/afraser/cpa_example/example.properties'

    p.load_file(filename)
    
    print p