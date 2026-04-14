from core.services.naver_blog import normalize_naver_blog_url


def test_normalize_naver_blog_url_from_query_format() -> None:
    normalized, post_id = normalize_naver_blog_url(
        "https://blog.naver.com/PostView.naver?blogId=parkmingkey&logNo=223980923579&redirect=Dlog"
    )
    assert normalized == "https://m.blog.naver.com/parkmingkey/223980923579"
    assert post_id == "223980923579"


def test_normalize_naver_blog_url_from_mobile_format() -> None:
    normalized, post_id = normalize_naver_blog_url("https://m.blog.naver.com/parkmingkey/223746232904")
    assert normalized == "https://m.blog.naver.com/parkmingkey/223746232904"
    assert post_id == "223746232904"
