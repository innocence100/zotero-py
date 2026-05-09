import json

from fastapi import APIRouter, Query, Response

from ..schema_data import ITEM_TYPES, get_item_template

router = APIRouter()


@router.get("/itemTypes")
async def list_item_types():
    types = [{"itemType": t} for t in ITEM_TYPES if t != "annotation"]
    return Response(content=json.dumps(types), media_type="application/json")


@router.get("/itemTypeFields")
async def get_item_type_fields(itemType: str = Query(...)):
    schema = ITEM_TYPES.get(itemType)
    if not schema:
        return Response(content="[]", media_type="application/json")

    fields = [{"field": f} for f in schema["fields"]]
    return Response(content=json.dumps(fields), media_type="application/json")


@router.get("/itemTypeCreatorTypes")
async def get_item_type_creator_types(itemType: str = Query(...)):
    schema = ITEM_TYPES.get(itemType)
    if not schema:
        return Response(content="[]", media_type="application/json")

    creators = [{"creatorType": c["creatorType"]} for c in schema["creators"]]
    return Response(content=json.dumps(creators), media_type="application/json")


@router.get("/creatorFields")
async def get_creator_fields():
    return Response(
        content=json.dumps([
            {"field": "firstName"},
            {"field": "lastName"},
            {"field": "name"},
        ]),
        media_type="application/json",
    )


@router.get("/itemFields")
async def list_item_fields():
    all_fields = set()
    for schema in ITEM_TYPES.values():
        for f in schema["fields"]:
            all_fields.add(f)
    fields = [{"field": f} for f in sorted(all_fields)]
    return Response(content=json.dumps(fields), media_type="application/json")


@router.get("/items/new")
async def new_item(
    itemType: str = Query("book"),
    annotationType: str = Query(None),
    linkMode: str = Query(None),
):
    template = get_item_template(itemType, annotationType, linkMode)
    if template is None:
        return Response(
            content=json.dumps({"error": f"Unknown item type: {itemType}"}),
            media_type="application/json",
            status_code=400,
        )
    return Response(content=json.dumps(template), media_type="application/json")
