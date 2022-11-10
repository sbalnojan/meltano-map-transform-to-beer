"""A sample inline mapper app."""

from pathlib import PurePath
from typing import Generator, List, Optional, Union

import singer_sdk.typing as th
from singer_sdk import _singerlib as singer
from singer_sdk.helpers._util import utc_now
from singer_sdk.mapper import PluginMapper
from singer_sdk.mapper_base import InlineMapper
import logging
import requests

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

class StreamTransform(InlineMapper):
    """A map transformer which implements the Stream Maps capability."""

    name = "meltano-map-transformer"

    config_jsonschema = th.PropertiesList(
        th.Property(
            "stream_maps",
            th.ObjectType(
                additional_properties=th.CustomType(
                    {
                        "type": ["object", "string", "null"],
                        "properties": {
                            "__filter__": {"type": ["string", "null"]},
                            "__source__": {"type": ["string", "null"]},
                            "__alias__": {"type": ["string", "null"]},
                            "__else__": {"type": ["null"]},
                            "__key_properties__": {
                                "type": ["array", "null"],
                                "items": {"type": "string"},
                            },
                        },
                        "additionalProperties": {"type": ["string", "null"]},
                    }
                )
            ),
            required=True,
            description="Stream maps",
        )
    ).to_dict()

    def __init__(
        self,
        config: Optional[Union[dict, PurePath, str, List[Union[PurePath, str]]]] = None,
        parse_env_config: bool = False,
        validate_config: bool = True,
    ) -> None:
        """Create a new inline mapper.

        Args:
            config: Mapper configuration. Can be a dictionary, a single path to a
                configuration file, or a list of paths to multiple configuration
                files.
            parse_env_config: Whether to look for configuration values in environment
                variables.
            validate_config: True to require validation of config settings.
        """
        super().__init__(
            config=config,
            parse_env_config=parse_env_config,
            validate_config=validate_config,
        )

        self.mapper = PluginMapper(plugin_config=dict(self.config), logger=self.logger)

    def map_schema_message(
        self,
        message_dict: dict,
    ) -> Generator[singer.Message, None, None]:
        """Map a schema message according to config.

        Args:
            message_dict: A SCHEMA message JSON dictionary.

        Yields:
            Transformed schema messages.
        """
        self._assert_line_requires(message_dict, requires={"stream", "schema"})

        stream_id: str = message_dict["stream"]
        self.mapper.register_raw_stream_schema(
            stream_id,
            message_dict["schema"],
            message_dict.get("key_properties", []),
        )
        for stream_map in self.mapper.stream_maps[stream_id]:
            schema_message = singer.SchemaMessage(
                stream_map.stream_alias,
                stream_map.transformed_schema,
                stream_map.transformed_key_properties,
                message_dict.get("bookmark_keys", []),
            )
            yield schema_message

    def map_record_message(
        self,
        message_dict: dict,
    ) -> Generator[singer.Message, None, None]:
        """Map a record message according to config.

        Args:
            message_dict: A RECORD message JSON dictionary.

        Yields:
            Transformed record messages.
        """
        self._assert_line_requires(message_dict, requires={"stream", "record"})



        stream_id: str = message_dict["stream"]
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

            if mapped_record is not None:
                record_message = singer.RecordMessage(
                    stream=stream_map.stream_alias,
                    record=mapped_record,
                    version=message_dict.get("version"),
                    time_extracted=utc_now(),
                )
                yield record_message

    def map_state_message(self, message_dict: dict) -> List[singer.Message]:
        """Do nothing to the message.

        Args:
            message_dict: A STATE message JSON dictionary.

        Returns:
            The same state message
        """
        return [singer.StateMessage(value=message_dict["value"])]

    def map_activate_version_message(
        self,
        message_dict: dict,
    ) -> Generator[singer.Message, None, None]:
        """Duplicate the message or alias the stream name as defined in configuration.

        Args:
            message_dict: An ACTIVATE_VERSION message JSON dictionary.

        Yields:
            An ACTIVATE_VERSION for each duplicated or aliased stream.
        """
        self._assert_line_requires(message_dict, requires={"stream", "version"})

        stream_id: str = message_dict["stream"]
        for stream_map in self.mapper.stream_maps[stream_id]:
            yield singer.ActivateVersionMessage(
                stream=stream_map.stream_alias,
                version=message_dict["version"],
            )
