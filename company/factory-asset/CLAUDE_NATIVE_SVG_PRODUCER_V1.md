# Claude Native SVG Producer Candidate v1

Task: `FA-320`

Claude is defined as a **candidate** `NATIVE_VECTOR` producer for `ICON` and `OUTLINE`. This task does not claim that the live Claude route is accepted.

A valid master must originate as SVG source text from the provider and remain editable vector geometry. Raster tracing, an SVG wrapper whose meaningful content is an embedded raster image, screenshots, and post-hoc raster-to-vector conversion cannot claim native-vector success.

The adapter freezes the exact Asset Blueprint v2 hash and exact provider-prompt hash into its idempotency key. It grants no provider-call, marketplace submission, publication, or route-promotion authority. FA-321 owns safety/editability/render QA and vector derivative validation; FA-322 owns the bounded live Claude ICON/OUTLINE acceptance and is the only task that may promote the route after passing.
