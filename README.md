## Meltano-map-transformer fork with added foobar & beer replacement
This is a fork of the [meltano-map-transformer](https://github.com/MeltanoLabs/meltano-map-transform) extended by two simple function with added capabilities.

1. A "foobar" function is able to replace string values by "foobar"
2. A "replace_with_beer" function is able to call a random data API and replace string values with a random beer name. 

## Usage
The added functions are used as transforms after the original maps are processed. 

You define them as additional stream_map_configs e.g:
```yaml
  - name: my-own
    namespace: meltano_map_trafonsform
    pip_url: /map_trafo
    executable: meltano-map-transform
    mappings:
    - name: hash_email
      config:
        stream_maps:
          customers:
            id: id
            email:      # drop the PII field from RECORD and SCHEMA messages
            email_domain: email.split('@')[-1]
            email_hash: md5(config['hash_seed'] + email)
            non_beer: email
            __else__: null
        stream_map_config:
          hash_seed: 01AWZh7A6DzGm6iJZZ2
          __foobar__: ["email_hash","email_domain"] # These two columns' values will be 
          # be replaced by foobar
          __beer__: ["non_beer"] # This one columns' values will be replaced by 
          # random beer names sourced from an external API
```

## Code Sneak Peek
All new code is located in the [mapper.py](map_trafo/meltano_map_transform/mapper.py) file.
The actual functionality is wrapped into two separate functions.
```Python
def foo_bar(input: str) -> str:
    """
    Turns every string into "foobar".
    """
    return "foobar"

def replace_with_beer(input: str) -> str:
    """
    Calls the random Data API for beers and replaces your string with a beer.
    """
    URL = "https://random-data-api.com/api/v2/beers"
    r = requests.get(url = URL)

    data = r.json()

    return data["name"]


FOOBAR_OPTION = "__foobar__"
BEER_OPTION = "__beer__"
```

As you can see, at the end we also define two markers for the config.

*Note: If you have a clear schema you want to transform, you could drop all of this and simply directly work with it. But that will lead to a very failure prone setup especially if schema changes happen.*

To insert our transformation we change the `map_record_message` function with the following addition: 

```python
        for stream_map in self.mapper.stream_maps[stream_id]:
            mapped_record = stream_map.transform(message_dict["record"])

            # This is my new magic...
            stream_map_config = self.config["stream_map_config"]
            if FOOBAR_OPTION in stream_map_config:
                foobar_columns = stream_map_config[FOOBAR_OPTION]

                for column in foobar_columns:
                    mapped_record[column] = foo_bar(mapped_record[column])

            if BEER_OPTION in stream_map_config:
                beer_columns = stream_map_config[BEER_OPTION]
                logging.info(f"Found {len(beer_columns)} beer columns: %s", beer_columns)
                for column in beer_columns:
                    mapped_record[column] = replace_with_beer(mapped_record[column])
                
            # logging.info("New record %s", mapped_record)
            # End of my terrible Python code
```

And that's it! If you want to change column types, you will also have to touch other functions, not just the record function.