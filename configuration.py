import sys
import json
from collections import MutableMapping

"""
Module to provide an interface to multiple sources of configuration:
    File (json)

The module implements the bridge pattern and uses the 'Configuration' object is the
point of entry. This will create a provider class depending on the string passed to it.

"""


class Configuration(object):

    def __init__(self, config_source):
        """
        Object to store all configuration values for the
        image bakery.

        :param config_source: dict containing the config source and connection settings
            This should contain at least the type and settings for the configuration:
            {
                "type": "File",
                "settings": {
                    "source": "my_config_file.json"
                    }
            }
            The Type will be used to pick the correct class for this config source.
            The settings will be used by the class to access the source
        :return:
        """

        # test and assign config_source
        if not config_source["type"]:
            raise ValueError("config_source should contain the source type")
        self.config_source = config_source

        # set the provider class depending on the config source
        self._provider = self.get_class()(self.config_source["settings"])

    def get_class(self):
        """
        Create the name of the required provider class from the config source
        :return: The name of the required class
        """
        return getattr(sys.modules[__name__], "ConfigurationProvider{}".format(self.config_source["type"]))

    def get_val(self, key=""):
        """
        Pass the key into the provider object's get_val() function
        :param key: The key to pass to the provider object's function
        :return: The result from the provider object's get_value() function
        """
        return self._provider.get_val(key)

    def set_val(self, key, value):
        """
        Pass the key into the provider object's set_val() function
        :param key: The key to pass to the provider object's function
        :param value: The value to pass to the provider object's function
        :return: The result from the provider object's set_value() function
        """
        return self._provider.set_val(key, value)

    def save(self):
        """
        Call the provider object's save() function
        :return: The result from the provider object's save() function
        """
        return self._provider.save()

    def import_config(self):
        """
        Call the provider object's import_config() function
        :return: The result from the provider object's import_config() function
        """
        return self._provider.import_config()

    def switch_provider(self, config_source, overwrite=False):
        """
        Change the provider object
        :param config_source: dict containing the new provider type and settings
        :param overwrite: Overwrite the application configuration with the
                configuration from the new provider (default is to keep the
                application config)
        :return:
        """
        # change the config_source
        self.config_source = config_source

        # initialise the new provider
        new_provider = self.get_class()(self.config_source["settings"])

        # copy data to the new provider if we are keeping the application config
        if not overwrite:
            new_provider.configuration = self._provider.configuration

        # make the new provider the current one
        self._provider = new_provider


class ConfigurationProvider(object):

    def __init__(self, config_settings):
        """
        The abstract class listing the functions all subclasses must
        implement and also implementing common functions.
        """
        self.config_settings = config_settings
        if self.import_config() == False:
            raise IOError("Unable to open the file at {} for reading. "
                          "Please check that it exists, has the correct "
                          "permissions and contains valid json.".format(config_settings['source']))

    def import_config(self):
        """
        Raise an error if the subclasses don't implement this function
        :return:
        """
        raise NotImplementedError("Must implement import_config()")

    def save_all(self):
        """
        Raise an error if the subclasses don't implement this function
        :return:
        """
        raise NotImplementedError("Must implement save_all()")

    def save_value(self, key, value):
        """
        Raise an error if the subclasses don't implement this function
        :return:
        """
        raise NotImplementedError("Must implement save_value()")

    def get_val(self, key=""):
        """
        Find and return the value for the provided key. multi-level

        :param key: The key to find
                keys should be provided with dot sytax e.g. 'key1.key2.key3'
                would find self.configuration["imagebakery"]["key1"]["key2"]["key3"]
        :return: Value at the position of the key provided or None if it doesn't exist
        """
        # if the key is an empty string (default) return all
        if key == "":
            return self.configuration

        try:
            return reduce(lambda d, k: d[k], key.split("."), self.configuration)
        except:
            return None

    def _search_and_replace(self, d, k, v):
        """
        Search for key 'k' in dict 'd' and add/replace with value 'v'
        :param d: dict to use
        :param k: key to search for
        :param v: value to add
        :return:
        """
        # Add the value to the application configuration
        key_list = k.split(".")
        keys, (newkey) = key_list[:-1], key_list[-1]

        temp_dict = d

        for key in keys:
            try:
                val = temp_dict[key]
            except KeyError:
                val = temp_dict[key] = dict()
            else:
                if not isinstance(val, MutableMapping):
                    val = temp_dict[key] = dict()
            temp_dict = val
        temp_dict[newkey] = v


    def set_val(self, key, value):
        """
        Find and update the value for the provided key

        :param key: The key to find
                keys should be provided with dot sytax e.g. 'key1.key2.key3'
                would find configuration["imagebakery"]["key1"]["key2"]["key3"]
                If the key doesn't exist, it will be created.
        :param value: The new value
        :return: Value at the position of the key provided or None if it doesn't exist
        """

        # Add the value to the application configuration
        self._search_and_replace(self.configuration, key, value)

        # save the value back to the source
        self.save_value(key, value)

        return self.get_val(key)


class ConfigurationProviderFile(ConfigurationProvider):

    def __init__(self, config_settings):
        """
        Object to represent when the configuration is from a File
        :return:
        """
        ConfigurationProvider.__init__(self, config_settings)

    def import_config(self):
        """
        Import the configuration into the application
        :return:
        """
        try:
            with open(self.config_settings["source"], "r") as config_file:
                self.configuration = json.load(config_file)
        except:
            # Error with the file - doesn't exist? permissions?
            return False

    def save_value(self, key, value):
        """
        Save a single value back to the configuration file.

        :param key: The key to save
        :param value: The value to save
        :return:
        """
        with open(self.config_settings["source"], "r") as config_file:
            temp_config = json.load(config_file)

        self._search_and_replace(temp_config, key, value)

        with open(self.config_settings["source"], "w+") as config_file:
            json.dump(temp_config,
                      config_file,
                      indent=4,
                      sort_keys=True,
                      ensure_ascii=False)

    def save_all(self):
        """
        Save the configuration to it's source file.
        :return: 0 on sucess
        """
        with open(self.config_settings["source"], "w+") as config_file:
            json.dump(self.configuration,
                      config_file,
                      indent=4,
                      sort_keys=True,
                      ensure_ascii=False)


class ConfigurationProviderConsul(ConfigurationProvider):

    def __init__(self, config_settings):
        """
        Object to represent when configuration is from Consul
        :return:
        """
        ConfigurationProvider.__init__(self, config_settings)

    def import_config(self):
        """
        Raise an error if the subclasses don't implement this function
        :return:
        """
        raise NotImplementedError("Must implement import_config()")

    def save_all(self):
        """
        Raise an error if the subclasses don't implement this function
        :return:
        """
        raise NotImplementedError("Must implement save()")

    def save_value(self, key, value):
        """
        Raise an error if the subclasses don't implement this function
        :return:
        """
        raise NotImplementedError("Must implement save_value()")


if __name__ == '__main__':

    # create an config object that uses LocalFile
    local_file_settings = {
                            "type":"File",
                            "settings":
                                {
                                    "source": "sample.json"
                                }
                           }

    consul_settings = {
                        "type":"Consul",
                        "settings":
                            {
                                "url": "localhost"
                            }
                        }

    #conf = Configuration(local_file_settings)
    conf = Configuration(consul_settings)

    print conf.set_val("employee.001.id", "001")
    print conf.set_val("employee.001.name", "Bob")
    print conf.set_val("employee.001.age", "27")
    print conf.set_val("employee.001.position", "Developer")

    print conf.set_val("employee.002.id", "002")
    print conf.set_val("employee.002.name", "Sarah")
    print conf.set_val("employee.002.age", "24")
    print conf.set_val("employee.002.position", "Project Manager")

    print conf.get_val()
    print conf.get_val("employee.002")

    #conf.save()



