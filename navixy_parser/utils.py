# Place your shared function here
def unpack_tag_value(tag_ordinal: int, tags_list: list[Tag], tag_bindings: list[TrackTagBindings]) -> str:
    """
    getting tag value
    """
    for track_tags in tag_bindings:
        if track_tags.ordinal == tag_ordinal:
            for tags in tags_list:
                if tags.id == track_tags.tag_id:
                    return tags.name
    return ''
