# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Dict, List, Literal, Optional, Union, cast, get_args
from uuid import uuid4

from pyrit.models.chat_message import ChatMessage, ChatMessageRole
from pyrit.models.literals import PromptDataType, PromptResponseError
from pyrit.models.score import Score

Originator = Literal["orchestrator", "converter", "undefined", "scorer"]


class PromptRequestPiece:
    """Represents a piece of a prompt request to a target.

    This class represents a single piece of a prompt request that will be sent
    to a target. Since some targets can handle multiple pieces (e.g., text and images),
    requests are composed of lists of PromptRequestPiece objects.
    """

    def __init__(
        self,
        *,
        role: ChatMessageRole,
        original_value: str,
        original_value_sha256: Optional[str] = None,
        converted_value: Optional[str] = None,
        converted_value_sha256: Optional[str] = None,
        id: Optional[uuid.UUID | str] = None,
        conversation_id: Optional[str] = None,
        sequence: int = -1,
        labels: Optional[Dict[str, str]] = None,
        prompt_metadata: Optional[Dict[str, Union[str, int]]] = None,
        converter_identifiers: Optional[List[Dict[str, str]]] = None,
        prompt_target_identifier: Optional[Dict[str, str]] = None,
        orchestrator_identifier: Optional[Dict[str, str]] = None,
        scorer_identifier: Optional[Dict[str, str]] = None,
        original_value_data_type: PromptDataType = "text",
        converted_value_data_type: PromptDataType = "text",
        response_error: PromptResponseError = "none",
        originator: Originator = "undefined",
        original_prompt_id: Optional[uuid.UUID] = None,
        timestamp: Optional[datetime] = None,
        scores: Optional[List[Score]] = None,
    ):
        """Initialize a PromptRequestPiece.

        Args:
            role: The role of the prompt (system, assistant, user).
            original_value: The text of the original prompt. If prompt is an image, it's a link.
            original_value_sha256: The SHA256 hash of the original prompt data. Defaults to None.
            converted_value: The text of the converted prompt. If prompt is an image, it's a link. Defaults to None.
            converted_value_sha256: The SHA256 hash of the converted prompt data. Defaults to None.
            id: The unique identifier for the memory entry. Defaults to None (auto-generated).
            conversation_id: The identifier for the conversation which is associated with a single target.
                Defaults to None.
            sequence: The order of the conversation within a conversation_id. Defaults to -1.
            labels: The labels associated with the memory entry. Several can be standardized. Defaults to None.
            prompt_metadata: The metadata associated with the prompt. This can be specific to any scenarios.
                Because memory is how components talk with each other, this can be component specific.
                e.g. the URI from a file uploaded to a blob store, or a document type you want to upload.
                Defaults to None.
            converter_identifiers: The converter identifiers for the prompt. Defaults to None.
            prompt_target_identifier: The target identifier for the prompt. Defaults to None.
            orchestrator_identifier: The orchestrator identifier for the prompt. Defaults to None.
            scorer_identifier: The scorer identifier for the prompt. Defaults to None.
            original_value_data_type: The data type of the original prompt (text, image). Defaults to "text".
            converted_value_data_type: The data type of the converted prompt (text, image). Defaults to "text".
            response_error: The response error type. Defaults to "none".
            originator: The originator of the prompt. Defaults to "undefined".
            original_prompt_id: The original prompt id. It is equal to id unless it is a duplicate. Defaults to None.
            timestamp: The timestamp of the memory entry. Defaults to None (auto-generated).
            scores: The scores associated with the prompt. Defaults to None.
        """

        self.id = id if id else uuid4()

        if role not in ChatMessageRole.__args__:  # type: ignore
            raise ValueError(f"Role {role} is not a valid role.")

        self.role = role

        if converted_value is None:
            converted_value = original_value
            converted_value_data_type = original_value_data_type

        self.conversation_id = conversation_id if conversation_id else str(uuid4())
        self.sequence = sequence

        self.timestamp = timestamp if timestamp else datetime.now()
        self.labels = labels or {}
        self.prompt_metadata = prompt_metadata or {}

        self.converter_identifiers = converter_identifiers if converter_identifiers else []

        self.prompt_target_identifier = prompt_target_identifier or {}
        self.orchestrator_identifier = orchestrator_identifier or {}
        self.scorer_identifier = scorer_identifier or {}

        self.original_value = original_value

        if original_value_data_type not in get_args(PromptDataType):
            raise ValueError(f"original_value_data_type {original_value_data_type} is not a valid data type.")

        self.original_value_data_type = original_value_data_type

        self.original_value_sha256 = original_value_sha256

        self.converted_value = converted_value

        if converted_value_data_type not in get_args(PromptDataType):
            raise ValueError(f"converted_value_data_type {converted_value_data_type} is not a valid data type.")

        self.converted_value_data_type = converted_value_data_type

        self.converted_value_sha256 = converted_value_sha256

        if response_error not in get_args(PromptResponseError):
            raise ValueError(f"response_error {response_error} is not a valid response error.")

        self.response_error = response_error
        self.originator = originator

        # Original prompt id defaults to id (assumes that this is the original prompt, not a duplicate)
        self.original_prompt_id = original_prompt_id or self.id

        self.scores = scores if scores else []

    async def set_sha256_values_async(self):
        """
        This method computes the SHA256 hash values asynchronously.
        It should be called after object creation if `original_value` and `converted_value` are set.

        Note, this method is async due to the blob retrieval. And because of that, we opted
        to take it out of main and setter functions. The disadvantage is that it must be explicitly called.
        """
        from pyrit.models.data_type_serializer import data_serializer_factory

        original_serializer = data_serializer_factory(
            category="prompt-memory-entries",
            data_type=cast(PromptDataType, self.original_value_data_type),
            value=self.original_value,
        )
        self.original_value_sha256 = await original_serializer.get_sha256()

        converted_serializer = data_serializer_factory(
            category="prompt-memory-entries",
            data_type=cast(PromptDataType, self.converted_value_data_type),
            value=self.converted_value,
        )
        self.converted_value_sha256 = await converted_serializer.get_sha256()

    def to_chat_message(self) -> ChatMessage:
        return ChatMessage(role=cast(ChatMessageRole, self.role), content=self.converted_value)

    def to_prompt_request_response(self) -> "PromptRequestResponse":  # type: ignore # noqa F821
        from pyrit.models.prompt_request_response import PromptRequestResponse

        return PromptRequestResponse([self])  # noqa F821

    def has_error(self) -> bool:
        """
        Check if the prompt request piece has an error.
        """
        return self.response_error != "none"

    def is_blocked(self) -> bool:
        """
        Check if the prompt request piece is blocked.
        """
        return self.response_error == "blocked"

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "role": self.role,
            "conversation_id": self.conversation_id,
            "sequence": self.sequence,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "labels": self.labels,
            "prompt_metadata": self.prompt_metadata,
            "converter_identifiers": self.converter_identifiers,
            "prompt_target_identifier": self.prompt_target_identifier,
            "orchestrator_identifier": self.orchestrator_identifier,
            "scorer_identifier": self.scorer_identifier,
            "original_value_data_type": self.original_value_data_type,
            "original_value": self.original_value,
            "original_value_sha256": self.original_value_sha256,
            "converted_value_data_type": self.converted_value_data_type,
            "converted_value": self.converted_value,
            "converted_value_sha256": self.converted_value_sha256,
            "response_error": self.response_error,
            "originator": self.originator,
            "original_prompt_id": str(self.original_prompt_id),
            "scores": [score.to_dict() for score in self.scores],
        }

    def __str__(self):
        return f"{self.prompt_target_identifier}: {self.role}: {self.converted_value}"

    __repr__ = __str__

    def __eq__(self, other) -> bool:
        return (
            self.id == other.id
            and self.role == other.role
            and self.original_value == other.original_value
            and self.original_value_data_type == other.original_value_data_type
            and self.original_value_sha256 == other.original_value_sha256
            and self.converted_value == other.converted_value
            and self.converted_value_data_type == other.converted_value_data_type
            and self.converted_value_sha256 == other.converted_value_sha256
            and self.conversation_id == other.conversation_id
            and self.sequence == other.sequence
        )


def sort_request_pieces(prompt_pieces: list[PromptRequestPiece]) -> list[PromptRequestPiece]:
    """
    Group by conversation_id.
    Order conversations by the earliest timestamp within each conversation_id.
    Within each conversation, order messages by sequence.
    """
    earliest_timestamps = {
        convo_id: min(x.timestamp for x in prompt_pieces if x.conversation_id == convo_id)
        for convo_id in {x.conversation_id for x in prompt_pieces}
    }

    # Sort using the precomputed timestamp values, then by sequence
    return sorted(prompt_pieces, key=lambda x: (earliest_timestamps[x.conversation_id], x.conversation_id, x.sequence))
