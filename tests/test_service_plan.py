from videopsalm import PassageItem, ServicePlan, SetListItem


def test_service_plan_uses_expected_passages_in_lead_translation() -> None:
    plan = ServicePlan(
        id='sunday',
        name='Sunday service',
        translation_id='kjv',
        language='en',
        items=(
            SetListItem('song', 'amazing-grace', 'Amazing Grace'),
            PassageItem('john 3:16', 'John 3:16', translation_id='kjv', language='en'),
        ),
    )
    assert plan.translation_id == 'kjv'
    assert plan.song_ids() == ('amazing-grace',)
    assert plan.passage_ids() == ('john 3:16',)


def test_passage_item_requires_reference_and_translation() -> None:
    try:
        PassageItem('', 'John 3:16')
        raise AssertionError('expected validation error')
    except ValueError:
        pass
