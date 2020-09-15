# Madoc Search Service API

## POSTing data

The service accepts a JSON POSTrequest at `iiif/` with headers:

```json
{"Content-Type": "application/json", "Accept": "application/json"}
```

The payload format is:

```json
{
  "contexts": 
    [
       {
          "id": "urn:madoc:site:2", 
          "type": "Site"
        },
       {
          "id": "https://example.org/collections/foo",
          "type": "Collection"
         }
     ],
  "resource": { },
  "id": "urn:madoc:manifest:foo",
  "thumbnail": "http://madoc.foo/thumbnail/foo/fake.jpg"
}
```

* contexts: List of contexts with identifier and type
* resource: the JSON for the IIIF resource
* id: the identifier (in Madoc) for the resource
* thumbnail: URL for the thumbnail (in Madoc) for the resource

## Query API

The search API is at `search/`. 

The basic query parameters are as follows


* `?fulltext=foo` : search against the preindexed fulltext (term vectors) for `foo`
* `?contexts__id=urn:madoc:site:2`: filter to just objects with that context (N.B. that's a double underscore)
* `?madoc_id=urn:madoc:manifest:saa-AA0428a`: filter to just hits within that one object (n.b. that's a single underscore)

In principle, we can add filters trivially easy for any other fields in the IIIF resource that make sense to filter on. 
They need to be added to a list of filterset_fields, but other than that, the code is already in place.

Querying for a facet:

* `?facet_type=metadata&facet_subtype=material&facet_value=paper&fulltext=Abbey`: filter the existing search results (for "Abbey") on metadata, where the metadata field "material" equals "paper"