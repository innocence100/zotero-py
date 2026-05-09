ITEM_TYPES = {
    "note": {"fields": ["note"], "creators": []},
    "book": {
        "fields": [
            "title", "abstractNote", "series", "seriesNumber", "volume",
            "numberOfVolumes", "edition", "place", "publisher", "date",
            "numPages", "language", "ISBN", "shortTitle", "url", "accessDate",
            "archive", "archiveLocation", "libraryCatalog", "callNumber", "rights",
            "extra",
        ],
        "creators": [
            {"creatorType": "author", "primary": True},
            {"creatorType": "contributor", "primary": False},
            {"creatorType": "editor", "primary": False},
            {"creatorType": "translator", "primary": False},
            {"creatorType": "seriesEditor", "primary": False},
        ],
    },
    "bookSection": {
        "fields": [
            "title", "abstractNote", "bookTitle", "series", "seriesNumber",
            "volume", "numberOfVolumes", "edition", "place", "publisher",
            "date", "pages", "language", "ISBN", "shortTitle", "url",
            "accessDate", "archive", "archiveLocation", "libraryCatalog",
            "callNumber", "rights", "extra",
        ],
        "creators": [
            {"creatorType": "author", "primary": True},
            {"creatorType": "contributor", "primary": False},
            {"creatorType": "editor", "primary": False},
            {"creatorType": "translator", "primary": False},
            {"creatorType": "seriesEditor", "primary": False},
            {"creatorType": "bookAuthor", "primary": False},
        ],
    },
    "journalArticle": {
        "fields": [
            "title", "abstractNote", "publicationTitle", "volume", "issue",
            "pages", "date", "series", "seriesTitle", "seriesText",
            "journalAbbreviation", "language", "DOI", "ISSN", "shortTitle",
            "url", "accessDate", "archive", "archiveLocation", "libraryCatalog",
            "callNumber", "rights", "extra",
        ],
        "creators": [
            {"creatorType": "author", "primary": True},
            {"creatorType": "contributor", "primary": False},
            {"creatorType": "editor", "primary": False},
            {"creatorType": "translator", "primary": False},
            {"creatorType": "reviewedAuthor", "primary": False},
        ],
    },
    "magazineArticle": {
        "fields": [
            "title", "abstractNote", "publicationTitle", "volume", "issue",
            "date", "pages", "language", "ISSN", "shortTitle", "url",
            "accessDate", "archive", "archiveLocation", "libraryCatalog",
            "callNumber", "rights", "extra",
        ],
        "creators": [
            {"creatorType": "author", "primary": True},
            {"creatorType": "contributor", "primary": False},
            {"creatorType": "translator", "primary": False},
            {"creatorType": "reviewedAuthor", "primary": False},
        ],
    },
    "newspaperArticle": {
        "fields": [
            "title", "abstractNote", "publicationTitle", "date", "edition",
            "section", "pages", "place", "language", "ISSN", "shortTitle",
            "url", "accessDate", "archive", "archiveLocation", "libraryCatalog",
            "callNumber", "rights", "extra",
        ],
        "creators": [
            {"creatorType": "author", "primary": True},
            {"creatorType": "contributor", "primary": False},
            {"creatorType": "translator", "primary": False},
            {"creatorType": "reviewedAuthor", "primary": False},
        ],
    },
    "thesis": {
        "fields": [
            "title", "abstractNote", "thesisType", "university", "place",
            "date", "numPages", "language", "shortTitle", "url", "accessDate",
            "archive", "archiveLocation", "libraryCatalog", "callNumber",
            "rights", "extra",
        ],
        "creators": [
            {"creatorType": "author", "primary": True},
            {"creatorType": "contributor", "primary": False},
        ],
    },
    "letter": {
        "fields": [
            "title", "abstractNote", "letterType", "date", "language",
            "shortTitle", "url", "accessDate", "archive", "archiveLocation",
            "libraryCatalog", "callNumber", "rights", "extra",
        ],
        "creators": [
            {"creatorType": "author", "primary": True},
            {"creatorType": "contributor", "primary": False},
            {"creatorType": "recipient", "primary": False},
        ],
    },
    "manuscript": {
        "fields": [
            "title", "abstractNote", "manuscriptType", "place", "date",
            "numPages", "language", "shortTitle", "url", "accessDate",
            "archive", "archiveLocation", "libraryCatalog", "callNumber",
            "rights", "extra",
        ],
        "creators": [
            {"creatorType": "author", "primary": True},
            {"creatorType": "contributor", "primary": False},
            {"creatorType": "translator", "primary": False},
        ],
    },
    "interview": {
        "fields": [
            "title", "abstractNote", "date", "interviewMedium", "language",
            "shortTitle", "url", "accessDate", "archive", "archiveLocation",
            "libraryCatalog", "callNumber", "rights", "extra",
        ],
        "creators": [
            {"creatorType": "interviewee", "primary": True},
            {"creatorType": "contributor", "primary": False},
            {"creatorType": "interviewer", "primary": False},
            {"creatorType": "translator", "primary": False},
        ],
    },
    "film": {
        "fields": [
            "title", "abstractNote", "genre", "distributor", "date",
            "videoRecordingFormat", "runningTime", "language", "shortTitle",
            "url", "accessDate", "archive", "archiveLocation", "libraryCatalog",
            "callNumber", "rights", "extra",
        ],
        "creators": [
            {"creatorType": "director", "primary": True},
            {"creatorType": "contributor", "primary": False},
            {"creatorType": "scriptwriter", "primary": False},
            {"creatorType": "producer", "primary": False},
        ],
    },
    "artwork": {
        "fields": [
            "title", "abstractNote", "artworkMedium", "artworkSize", "date",
            "language", "shortTitle", "url", "accessDate", "archive",
            "archiveLocation", "libraryCatalog", "callNumber", "rights", "extra",
        ],
        "creators": [
            {"creatorType": "artist", "primary": True},
            {"creatorType": "contributor", "primary": False},
        ],
    },
    "webpage": {
        "fields": [
            "title", "abstractNote", "websiteTitle", "websiteType", "date",
            "shortTitle", "url", "accessDate", "language", "rights", "extra",
        ],
        "creators": [
            {"creatorType": "author", "primary": True},
            {"creatorType": "contributor", "primary": False},
            {"creatorType": "translator", "primary": False},
        ],
    },
    "attachment": {
        "fields": ["title", "url", "accessDate"],
        "creators": [],
    },
    "report": {
        "fields": [
            "title", "abstractNote", "reportNumber", "reportType",
            "seriesTitle", "institution", "date", "pages", "language",
            "shortTitle", "url", "accessDate", "archive", "archiveLocation",
            "libraryCatalog", "callNumber", "rights", "extra",
        ],
        "creators": [
            {"creatorType": "author", "primary": True},
            {"creatorType": "contributor", "primary": False},
            {"creatorType": "translator", "primary": False},
            {"creatorType": "seriesEditor", "primary": False},
        ],
    },
    "bill": {
        "fields": [
            "title", "abstractNote", "billNumber", "code", "codeVolume",
            "section", "codePages", "legislativeBody", "session", "history",
            "date", "language", "url", "accessDate", "shortTitle", "rights",
            "extra",
        ],
        "creators": [
            {"creatorType": "sponsor", "primary": True},
            {"creatorType": "contributor", "primary": False},
            {"creatorType": "cosponsor", "primary": False},
        ],
    },
    "case": {
        "fields": [
            "caseName", "abstractNote", "reporter", "reporterVolume",
            "court", "docketNumber", "firstPage", "history", "dateDecided",
            "language", "url", "accessDate", "shortTitle", "rights", "extra",
        ],
        "creators": [
            {"creatorType": "author", "primary": True},
            {"creatorType": "contributor", "primary": False},
            {"creatorType": "counsel", "primary": False},
        ],
    },
    "hearing": {
        "fields": [
            "title", "abstractNote", "committee", "legislativeBody",
            "session", "documentNumber", "numberOfVolumes", "place",
            "publisher", "date", "pages", "history", "language", "url",
            "accessDate", "shortTitle", "rights", "extra",
        ],
        "creators": [
            {"creatorType": "contributor", "primary": True},
        ],
    },
    "patent": {
        "fields": [
            "title", "abstractNote", "place", "country", "assignee",
            "issuingAuthority", "patentNumber", "filingDate", "applicationNumber",
            "issueDate", "priorityNumbers", "references", "legalStatus",
            "language", "url", "accessDate", "shortTitle", "rights", "extra",
        ],
        "creators": [
            {"creatorType": "inventor", "primary": True},
            {"creatorType": "contributor", "primary": False},
            {"creatorType": "attorneyAgent", "primary": False},
        ],
    },
    "statute": {
        "fields": [
            "nameOfAct", "abstractNote", "code", "codeNumber", "publicLawNumber",
            "dateEnacted", "codeVolume", "section", "codePages", "session",
            "history", "language", "url", "accessDate", "shortTitle", "rights",
            "extra",
        ],
        "creators": [
            {"creatorType": "author", "primary": True},
            {"creatorType": "contributor", "primary": False},
        ],
    },
    "email": {
        "fields": [
            "subject", "abstractNote", "date", "shortTitle", "url",
            "accessDate", "language", "rights", "extra",
        ],
        "creators": [
            {"creatorType": "author", "primary": True},
            {"creatorType": "contributor", "primary": False},
            {"creatorType": "recipient", "primary": False},
        ],
    },
    "map": {
        "fields": [
            "title", "abstractNote", "mapType", "scale", "seriesTitle",
            "edition", "place", "publisher", "date", "volume", "numberOfVolumes",
            "language", "ISBN", "url", "accessDate", "archive",
            "archiveLocation", "libraryCatalog", "callNumber", "rights", "extra",
        ],
        "creators": [
            {"creatorType": "cartographer", "primary": True},
            {"creatorType": "contributor", "primary": False},
            {"creatorType": "seriesEditor", "primary": False},
        ],
    },
    "blogPost": {
        "fields": [
            "title", "abstractNote", "blogTitle", "websiteType", "date",
            "url", "accessDate", "language", "shortTitle", "rights", "extra",
        ],
        "creators": [
            {"creatorType": "author", "primary": True},
            {"creatorType": "contributor", "primary": False},
            {"creatorType": "commenter", "primary": False},
        ],
    },
    "instantMessage": {
        "fields": [
            "title", "abstractNote", "date", "language", "shortTitle",
            "url", "accessDate", "rights", "extra",
        ],
        "creators": [
            {"creatorType": "author", "primary": True},
            {"creatorType": "contributor", "primary": False},
            {"creatorType": "recipient", "primary": False},
        ],
    },
    "forumPost": {
        "fields": [
            "title", "abstractNote", "forumTitle", "postType", "date",
            "language", "shortTitle", "url", "accessDate", "rights", "extra",
        ],
        "creators": [
            {"creatorType": "author", "primary": True},
            {"creatorType": "contributor", "primary": False},
        ],
    },
    "audioRecording": {
        "fields": [
            "title", "abstractNote", "audioRecordingFormat", "seriesTitle",
            "volume", "numberOfVolumes", "place", "label", "date", "runningTime",
            "language", "ISBN", "shortTitle", "url", "accessDate", "archive",
            "archiveLocation", "libraryCatalog", "callNumber", "rights", "extra",
        ],
        "creators": [
            {"creatorType": "performer", "primary": True},
            {"creatorType": "contributor", "primary": False},
            {"creatorType": "composer", "primary": False},
            {"creatorType": "wordsBy", "primary": False},
        ],
    },
    "presentation": {
        "fields": [
            "title", "abstractNote", "presentationType", "meetingName",
            "place", "date", "url", "accessDate", "language", "shortTitle",
            "rights", "extra",
        ],
        "creators": [
            {"creatorType": "presenter", "primary": True},
            {"creatorType": "contributor", "primary": False},
        ],
    },
    "videoRecording": {
        "fields": [
            "title", "abstractNote", "videoRecordingFormat", "seriesTitle",
            "volume", "numberOfVolumes", "place", "studio", "date", "runningTime",
            "language", "ISBN", "shortTitle", "url", "accessDate", "archive",
            "archiveLocation", "libraryCatalog", "callNumber", "rights", "extra",
        ],
        "creators": [
            {"creatorType": "director", "primary": True},
            {"creatorType": "contributor", "primary": False},
            {"creatorType": "scriptwriter", "primary": False},
            {"creatorType": "producer", "primary": False},
            {"creatorType": "castMember", "primary": False},
        ],
    },
    "tvBroadcast": {
        "fields": [
            "title", "abstractNote", "programTitle", "episodeNumber",
            "videoRecordingFormat", "network", "place", "date", "runningTime",
            "language", "shortTitle", "url", "accessDate", "archive",
            "archiveLocation", "libraryCatalog", "callNumber", "rights", "extra",
        ],
        "creators": [
            {"creatorType": "director", "primary": True},
            {"creatorType": "contributor", "primary": False},
            {"creatorType": "scriptwriter", "primary": False},
            {"creatorType": "producer", "primary": False},
            {"creatorType": "castMember", "primary": False},
            {"creatorType": "guest", "primary": False},
        ],
    },
    "radioBroadcast": {
        "fields": [
            "title", "abstractNote", "programTitle", "episodeNumber",
            "audioRecordingFormat", "network", "place", "date", "runningTime",
            "language", "shortTitle", "url", "accessDate", "archive",
            "archiveLocation", "libraryCatalog", "callNumber", "rights", "extra",
        ],
        "creators": [
            {"creatorType": "director", "primary": True},
            {"creatorType": "contributor", "primary": False},
            {"creatorType": "scriptwriter", "primary": False},
            {"creatorType": "producer", "primary": False},
            {"creatorType": "castMember", "primary": False},
            {"creatorType": "guest", "primary": False},
        ],
    },
    "podcast": {
        "fields": [
            "title", "abstractNote", "seriesTitle", "episodeNumber",
            "audioFileType", "runningTime", "url", "accessDate", "language",
            "shortTitle", "rights", "extra",
        ],
        "creators": [
            {"creatorType": "podcaster", "primary": True},
            {"creatorType": "contributor", "primary": False},
            {"creatorType": "guest", "primary": False},
        ],
    },
    "computerProgram": {
        "fields": [
            "title", "abstractNote", "versionNumber", "system", "place",
            "company", "date", "programmingLanguage", "ISBN", "shortTitle",
            "url", "accessDate", "archive", "archiveLocation", "libraryCatalog",
            "callNumber", "rights", "extra",
        ],
        "creators": [
            {"creatorType": "programmer", "primary": True},
            {"creatorType": "contributor", "primary": False},
        ],
    },
    "conferencePaper": {
        "fields": [
            "title", "abstractNote", "date", "proceedingsTitle", "conferenceName",
            "place", "publisher", "volume", "pages", "series", "language",
            "DOI", "ISBN", "shortTitle", "url", "accessDate", "archive",
            "archiveLocation", "libraryCatalog", "callNumber", "rights", "extra",
        ],
        "creators": [
            {"creatorType": "author", "primary": True},
            {"creatorType": "contributor", "primary": False},
            {"creatorType": "editor", "primary": False},
            {"creatorType": "translator", "primary": False},
            {"creatorType": "seriesEditor", "primary": False},
        ],
    },
    "document": {
        "fields": [
            "title", "abstractNote", "publisher", "date", "language",
            "shortTitle", "url", "accessDate", "archive", "archiveLocation",
            "libraryCatalog", "callNumber", "rights", "extra",
        ],
        "creators": [
            {"creatorType": "author", "primary": True},
            {"creatorType": "contributor", "primary": False},
            {"creatorType": "editor", "primary": False},
            {"creatorType": "translator", "primary": False},
            {"creatorType": "reviewedAuthor", "primary": False},
        ],
    },
    "encyclopediaArticle": {
        "fields": [
            "title", "abstractNote", "encyclopediaTitle", "series", "seriesNumber",
            "volume", "numberOfVolumes", "edition", "place", "publisher", "date",
            "pages", "language", "ISBN", "shortTitle", "url", "accessDate",
            "archive", "archiveLocation", "libraryCatalog", "callNumber", "rights",
            "extra",
        ],
        "creators": [
            {"creatorType": "author", "primary": True},
            {"creatorType": "contributor", "primary": False},
            {"creatorType": "editor", "primary": False},
            {"creatorType": "translator", "primary": False},
            {"creatorType": "seriesEditor", "primary": False},
        ],
    },
    "dictionaryEntry": {
        "fields": [
            "title", "abstractNote", "dictionaryTitle", "series", "seriesNumber",
            "volume", "numberOfVolumes", "edition", "place", "publisher", "date",
            "pages", "language", "ISBN", "shortTitle", "url", "accessDate",
            "archive", "archiveLocation", "libraryCatalog", "callNumber", "rights",
            "extra",
        ],
        "creators": [
            {"creatorType": "author", "primary": True},
            {"creatorType": "contributor", "primary": False},
            {"creatorType": "editor", "primary": False},
            {"creatorType": "translator", "primary": False},
            {"creatorType": "seriesEditor", "primary": False},
        ],
    },
    "annotation": {
        "fields": [
            "annotationType", "annotationText", "annotationComment",
            "annotationColor", "annotationPageLabel", "annotationSortIndex",
            "annotationPosition", "annotationAuthorName",
        ],
        "creators": [],
    },
}


def get_item_template(item_type: str, annotation_type: str = None, link_mode: str = None) -> dict:
    if item_type == "annotation":
        return _get_annotation_template(annotation_type)
    if item_type == "attachment":
        return _get_attachment_template(link_mode)
    if item_type == "note":
        return {
            "itemType": "note",
            "note": "",
            "tags": [],
            "collections": [],
            "relations": {},
        }

    schema = ITEM_TYPES.get(item_type)
    if not schema:
        return None

    template = {"itemType": item_type}
    for field in schema["fields"]:
        template[field] = ""

    if schema["creators"]:
        primary = next((c for c in schema["creators"] if c["primary"]), schema["creators"][0])
        template["creators"] = [{"creatorType": primary["creatorType"], "firstName": "", "lastName": ""}]
    else:
        template["creators"] = []

    template["tags"] = []
    template["collections"] = []
    template["relations"] = {}
    return template


def _get_annotation_template(annotation_type: str = "highlight") -> dict:
    t = {
        "itemType": "annotation",
        "parentItem": "",
        "annotationType": annotation_type or "highlight",
        "annotationComment": "",
        "annotationColor": "",
        "annotationPageLabel": "",
        "annotationSortIndex": "00000|000000|00000",
        "annotationPosition": {"pageIndex": 0, "rects": []},
    }
    if annotation_type in ("highlight", "underline"):
        t["annotationText"] = ""
    if annotation_type == "ink":
        t["annotationPosition"] = {"pageIndex": 0, "paths": [], "width": 2}
    if annotation_type == "image":
        t["annotationPosition"] = {"pageIndex": 0, "rects": [], "width": 0, "height": 0}
    return t


def _get_attachment_template(link_mode: str = "imported_file") -> dict:
    t = {"itemType": "attachment", "linkMode": link_mode or "imported_file"}
    if link_mode == "linked_url":
        t.update({"title": "", "url": "", "accessDate": "", "contentType": "", "charset": ""})
    elif link_mode == "linked_file":
        t.update({"title": "", "path": "", "contentType": "", "charset": ""})
    elif link_mode == "imported_url":
        t.update({"title": "", "url": "", "accessDate": "", "contentType": "", "charset": "", "md5": None, "mtime": None})
    elif link_mode == "imported_file":
        t.update({"title": "", "filename": "", "contentType": "", "charset": "", "md5": None, "mtime": None})
    elif link_mode == "embedded_image":
        t.update({"parentItem": "", "filename": "", "contentType": "", "md5": None, "mtime": None})
        return t
    else:
        t.update({"title": "", "contentType": "", "charset": ""})
    t["tags"] = []
    t["collections"] = []
    t["relations"] = {}
    return t
