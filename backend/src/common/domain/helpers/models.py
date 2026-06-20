from pydantic import BaseModel


def override_model_properties[T: BaseModel](
    target: T,
    source: BaseModel | dict,
    exclude_none: bool = True,
    exclude_unset: bool = False,
) -> T:
    """
    Update a BaseModel instance with values from another BaseModel or dict.

    Args:
        target: The BaseModel instance to update
        source: The source data (BaseModel or dict) to update from
        exclude_none: If True, None values are not copied (default: True)
        exclude_unset: If True, unset values are not copied (default: False)

    Returns:
        The updated target model
    """
    if isinstance(source, BaseModel):
        source_data = source.model_dump(exclude_none=exclude_none, exclude_unset=exclude_unset)
    else:
        source_data = {k: v for k, v in source.items() if not (exclude_none and v is None)}

    for field, value in source_data.items():
        if hasattr(target, field):
            setattr(target, field, value)

    return target


def override_dict_properties(target: object, source: dict) -> object:
    for key, value in source.items():
        if hasattr(target, key):
            setattr(target, key, value)
