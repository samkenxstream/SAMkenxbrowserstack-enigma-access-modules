import pytest

from . import constants, helpers, access


class MockBoto3:
    def add_user_to_group(self, GroupName, UserName):
        pass

    def remove_user_from_group(self, GroupName, UserName):
        pass

    def list_groups(Marker=None):
        return {
            "Groups": [
                {
                    "Path": "/",
                    "GroupName": "Group 1",
                    "GroupId": "1",
                    "Arn": "Group1",
                    "CreateDate": "2023-01-01",
                },
                {
                    "Path": "/",
                    "GroupName": "Group 2",
                    "GroupId": "2",
                    "Arn": "Group2",
                    "CreateDate": "2023-01-01",
                },
            ],
            "IsTruncated": False,
            "Marker": None,
        }


class MockBoto3withException(MockBoto3):
    def add_user_to_group(GroupName, UserName):
        raise Exception

    def remove_user_from_group(GroupName, UserName):
        raise Exception


def test_get_aws_credentails(*args, **kwargs):
    value = helpers._get_aws_credentails("test")
    assert type(value) == dict


@pytest.mark.parametrize(
    """test_name, user_email, label, expected_return_value, boto3_client""",
    [
        (
            "Grant AWS access - Success",
            "test@example.com",
            {"action": constants.GROUP_ACCESS, "account": "test", "group": "test"},
            True,
            MockBoto3(),
        ),
        (
            "Grant AWS access - Failure",
            "test@example.com",
            {"action": constants.GROUP_ACCESS, "account": "test", "group": "test"},
            False,
            MockBoto3withException(),
        ),
    ],
)
def test_grant_aws_access(
    mocker, test_name, user_email, label, expected_return_value, boto3_client
):
    userMock = mocker.MagicMock()
    userMock.email = user_email

    mocker.patch(
        "Access.access_modules.aws_access.helpers.get_aws_client",
        return_value=boto3_client,
    )
    mocker.patch("bootprocess.general.emailSES", return_value="")

    return_value, _ = helpers.grant_aws_access(
        userMock, label["account"], label["group"]
    )
    assert return_value == expected_return_value


@pytest.mark.parametrize(
    """test_name, user_email, label, expected_return_value, boto3_client""",
    [
        (
            "Revoke AWS access - Success",
            "test@example.com",
            {"action": constants.GROUP_ACCESS, "account": "test", "group": "test"},
            True,
            MockBoto3(),
        ),
        (
            "Revoke AWS access - Failure",
            "test@example.com",
            {"action": constants.GROUP_ACCESS, "account": "test", "group": "test"},
            False,
            MockBoto3withException(),
        ),
    ],
)
def test_revoke_aws_access(
    mocker, test_name, user_email, label, expected_return_value, boto3_client
):

    userMock = mocker.MagicMock()
    userMock.email = user_email

    request = mocker.MagicMock()
    request.request_id = "123"

    mocker.patch(
        "Access.access_modules.aws_access.helpers.get_aws_client",
        return_value=boto3_client,
    )

    return_value, _ = helpers.revoke_aws_access(
        userMock, label["account"], label["group"]
    )
    assert return_value == expected_return_value


def test_AWSAccess(mocker):
    userMock = mocker.MagicMock()
    userMock.email = "test@example.com"
    userMock.username = "user"

    requestMock = mocker.MagicMock()
    requestMock.user = userMock

    aws_access = access.AWSAccess()

    label_1 = {
        "action": constants.GROUP_ACCESS,
        "account": "test 1",
        "group": "test 1",
    }
    label_2 = {
        "action": constants.GROUP_ACCESS,
        "account": "test 2",
        "group": "test 2",
    }
    label_desc = aws_access.get_label_desc(access_label=label_1)
    assert label_desc == "GroupAccess for group: test 1"

    combined_label_desc = aws_access.combine_labels_desc(
        access_labels=[label_1, label_2]
    )
    assert (
        combined_label_desc
        == "GroupAccess for group: test 1, GroupAccess for group: test 2"
    )

    label_meta = aws_access.get_label_meta(access_label=label_1)
    assert label_meta == label_1

    expected_combined_meta = {
        "action": label_1["action"] + ", " + label_2["action"],
        "account": label_1["account"] + ", " + label_2["account"],
        "group": str(label_1["group"]) + ", " + str(label_2["group"]),
    }
    combined_label_meta = aws_access.combine_labels_meta(
        access_labels=[label_1, label_2]
    )
    assert combined_label_meta == expected_combined_meta

    assert type(aws_access.access_request_data("test")) == dict
    assert aws_access.validate_request([label_1], None) == [label_1]

    mocker.patch(
        "Access.access_modules.aws_access.helpers.grant_aws_access",
        return_value=(True, ""),
    )
    mocker.patch(
        "Access.access_modules.aws_access.helpers.revoke_aws_access",
        return_value=(True, ""),
    )

    return_value = aws_access.approve(userMock, [label_1], None, requestMock)
    assert return_value is True

    return_value = aws_access.revoke(userMock, label_1, requestMock)
    assert return_value is True


def test_get_aws_accounts(mocker):
    accounts = helpers.get_aws_accounts()
    assert type(accounts) == list


def test_get_aws_groups(mocker):
    mocker.patch(
        "Access.access_modules.aws_access.helpers.get_aws_client",
        return_value=MockBoto3(),
    )
    group_data = helpers.get_aws_groups(account="test", marker=None)
    assert "Groups" in group_data
    assert len(group_data["Groups"]) == 2