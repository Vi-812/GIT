import analytical.use_graphql as ug
import analytical.func_api_client as fa
import analytical.bug_issues as bi
from datetime import datetime
from app import logger


class GithubApiClient:
    """
    ОПИСАТЕЛЬНОЕ ОПИСАНИЕ
    """

    def __init__(self, token):
        self.token = token

    def get_new_report(self, repository_path, json_type='full'):
        """

        :param repository_path:
        :param json_type:
        :return:
        """
        self.request_duration_time = datetime.now()
        self.return_json = {}
        self.bug_issues_total_count = 0
        try:
            repository_path = repository_path.split('/')
            self.repository_owner, self.repository_name = repository_path[-2], repository_path[-1]
        except IndexError as e:
            print(repository_path + ' DDD')
            fa.path_error_400(e)
            return fa.path_error_400(e)

        self.request_total_cost = 0
        self.json_type = json_type

        self.get_info_labels()
        if self.return_json.get('queryInfo'):
            if self.return_json.get('queryInfo').get('code') == 404 \
                    or self.return_json.get('queryInfo').get('code') == 500:
                return self.return_json
        self.get_bug_issues()
        self.main_analytic_unit()
        self.forming_json()
        return self.return_json

    def get_info_labels(self):
        self.cursor = None
        self.r_time = None
        self.repo_version = None
        self.repo_major_version = None
        self.repo_minor_version = None
        self.repo_patch_version = None
        self.repo_pr_closed_count = None
        self.repo_pr_closed_duration = None
        self.repo_labels_name_list = []

        while True:
            data_github = ug.UseGraphQL(self.repository_owner,
                                                 self.repository_name,
                                                 self.cursor,
                                                 self.token)
            self.data = data_github.get_info_labels_json()
            if self.data.get('queryInfo'):
                if self.data.get('queryInfo').get('code') == 500:
                    self.return_json = self.data
                    return
            self.parse_info_labels()
            if self.return_json.get('queryInfo'):
                if self.return_json.get('queryInfo').get('code') == 404:
                    return
            if self.has_next_page:
                self.cursor = self.end_cursor
            else:
                break

        self.repo_labels_bug_list = []
        for name in self.repo_labels_name_list:
            if 'bug' in name.lower():
                self.repo_labels_bug_list.append(name)

    def parse_info_labels(self):
        try:
            if not self.cursor:
                self.repo_name = self.data['data']['repository']['name']
                self.repo_owner_login = self.data['data']['repository']['owner']['login']
                fa.owner_name(self.repo_owner_login, self.repo_name)
                self.repo_description = self.data['data']['repository']['description']
                self.repo_stars_count = self.data['data']['repository']['stargazerCount']
                self.repo_created_at = self.data['data']['repository']['createdAt']
                self.repo_updated_at = self.data['data']['repository']['updatedAt']
                self.repo_pushed_at = self.data['data']['repository']['pushedAt']
                self.repo_is_archived_bool = self.data['data']['repository']['isArchived']
                self.repo_is_locked_bool = self.data['data']['repository']['isLocked']
                self.repo_issues_total_count = self.data['data']['repository']['issues']['totalCount']
                self.repo_watchers_total_count = self.data['data']['repository']['watchers']['totalCount']
                self.repo_fork_total_count = self.data['data']['repository']['forkCount']
                self.repo_labels_total_count = self.data['data']['repository']['labels']['totalCount']
                if self.data['data']['repository']['releases']['edges']:
                    self.repo_version = self.data['data']['repository']['releases']['edges'][0]['node']['tag']['name']
                    version = fa.parsing_version(self.data['data']['repository']['releases']['edges'])
                    self.repo_major_version = version[0]
                    self.repo_minor_version = version[1]
                    self.repo_patch_version = version[2]
                if self.data['data']['repository']['pullRequests']['nodes']:
                    closed_pr = fa.pull_request_analytics(self.data['data']['repository']['pullRequests']['nodes'])
                    self.repo_pr_closed_count = closed_pr[0]
                    self.repo_pr_closed_duration = closed_pr[1]
            self.start_cursor = self.data['data']['repository']['labels']['pageInfo']['startCursor']
            self.end_cursor = self.data['data']['repository']['labels']['pageInfo']['endCursor']
            self.has_next_page = self.data['data']['repository']['labels']['pageInfo']['hasNextPage']
            for label in self.data['data']['repository']['labels']['edges']:
                self.repo_labels_name_list.append(label['node']['name'])
            self.request_cost = self.data['data']['rateLimit']['cost']
            self.request_total_cost += self.request_cost
            self.request_balance = self.data['data']['rateLimit']['remaining']
            self.request_reset = self.data['data']['rateLimit']['resetAt']
        except (TypeError, KeyError) as err:
            self.json_error_401_404(err)

    def get_bug_issues(self):
        self.cursor = None
        self.instance_b_i_a = bi.BugIssuesAnalytic()

        while True:
            data_github = ug.UseGraphQL(self.repository_owner,
                                                 self.repository_name,
                                                 self.cursor,
                                                 self.token,
                                                 self.repo_labels_bug_list)
            self.data = data_github.get_bug_issues_json()
            self.parse_bug_issues()
            if not self.cursor and self.bug_issues_total_count > 200:
                # Предварительный расчет времени запроса
                cost_multiplier = 2.7
                cost_upped = cost_multiplier * 2
                self.r_time = round(((self.bug_issues_total_count // 100) * cost_multiplier) + cost_upped, 2)
            if self.has_next_page:
                self.cursor = self.end_cursor
            else:
                break

    def parse_bug_issues(self):
        self.bug_issues_total_count = self.data['data']['repository']['issues']['totalCount']
        self.start_cursor = self.data['data']['repository']['issues']['pageInfo']['startCursor']
        self.end_cursor = self.data['data']['repository']['issues']['pageInfo']['endCursor']
        self.has_next_page = self.data['data']['repository']['issues']['pageInfo']['hasNextPage']
        if self.data['data']['repository']['issues']['edges']:
            self.instance_b_i_a.push_bug_issues(self.data['data']['repository']['issues']['edges'])
        self.request_cost = self.data['data']['rateLimit']['cost']
        self.request_total_cost += self.request_cost
        self.request_balance = self.data['data']['rateLimit']['remaining']
        self.request_reset = self.data['data']['rateLimit']['resetAt']

    def main_analytic_unit(self):
        self.messages_info = []
        self.messages_warning = []

        bug_analytic = self.instance_b_i_a.get_bug_analytic()
        self.bug_issues_closed_total_count = bug_analytic[0]
        self.bug_issues_open_total_count = bug_analytic[1]
        if self.bug_issues_total_count:
            self.bug_issues_no_comment = round(bug_analytic[2] / self.bug_issues_total_count * 100, 2)
        else:
            self.bug_issues_no_comment = None
        self.duration_closed_bug_min = bug_analytic[3]
        self.duration_closed_bug_max = bug_analytic[4]
        self.duration_closed_bug_95percent = bug_analytic[5]
        self.duration_closed_bug_50percent = bug_analytic[6]
        self.duration_open_bug_min = bug_analytic[7]
        self.duration_open_bug_max = bug_analytic[8]
        self.duration_open_bug_50percent = bug_analytic[9]
        self.bug_issues_closed_two_months = bug_analytic[10]
        if self.bug_issues_closed_total_count and self.bug_issues_closed_two_months:
             self.bug_issues_closed_two_months = round(self.bug_issues_closed_two_months \
                                                 / self.bug_issues_closed_total_count * 100, 2)
        else:
            self.bug_issues_closed_two_months = None

        self.preparation_info_data_block()
        self.preparation_badissues_data_block()
        self.analytic_repository_block()
        self.analytic_bug_issues_block()

    def preparation_info_data_block(self):
        self.repo_created_at = fa.to_date(self.repo_created_at)
        self.repo_updated_at = fa.to_date(self.repo_updated_at)
        self.repo_pushed_at = fa.to_date(self.repo_pushed_at)
        self.request_reset = fa.to_date(self.request_reset)

    def preparation_badissues_data_block(self):
        pass

    def analytic_repository_block(self):
        self.repo_duration = (datetime.now() - self.repo_created_at).days
        self.repo_updated_at = (datetime.now() - self.repo_updated_at).days
        self.repo_pushed_at = (datetime.now() - self.repo_pushed_at).days

    def analytic_bug_issues_block(self):
        pass

    def forming_json(self):
        # datetime str ???
        self.request_duration_time = datetime.now() - self.request_duration_time
        self.request_duration_time = round(self.request_duration_time.seconds +
                                           (self.request_duration_time.microseconds*0.000001), 2)
        if self.r_time:
            self.r_time = str(self.r_time) + '/' + str(self.request_duration_time)

        self.return_json = {
            'repositoryInfo': {
                'name': self.repo_name,
                'owner': self.repo_owner_login,
                'description': self.repo_description,
                'stars': self.repo_stars_count,
                'version': self.repo_version,
                'createdAt': str(self.repo_created_at),
                'duration': self.repo_duration,
                'updatedAt': self.repo_updated_at,
                'pushedAt': self.repo_pushed_at,
                'isArchived': self.repo_is_archived_bool,
                'isLocked': self.repo_is_locked_bool,
                'issuesCount': self.repo_issues_total_count,
                'bugIssuesCount': self.bug_issues_total_count,
                'bugIssuesClosedCount': self.bug_issues_closed_total_count,
                'bugIssuesOpenCount': self.bug_issues_open_total_count,
                'watchersCount': self.repo_watchers_total_count,
                'forkCount': self.repo_fork_total_count,
            },
            'analytic': {
                'bugsClosedTime95percent': self.duration_closed_bug_95percent,
                'bugsClosedTime50percent': self.duration_closed_bug_50percent,
                'majorDaysPassed': self.repo_major_version,
                'minorDaysPassed': self.repo_minor_version,
                'patchDaysPassed': self.repo_patch_version,
                'percentIssuesNoComment': self.bug_issues_no_comment,
                'percentIssuesClosed2months': self.bug_issues_closed_two_months,
                'pullRequestClosed2months': self.repo_pr_closed_count,
                'medianDurationPullRequest': self.repo_pr_closed_duration,
            },
            'queryInfo': {

                'time': str(self.request_duration_time),
                'cost': self.request_total_cost,
                'remaining': self.request_balance,
                'resetAt': str(self.request_reset),
                'rt': self.r_time,
                'database': None,
                'code': 200,
            },
        }

    def json_error_401_404(self, error):
        logger.error(f'E404! Не найден репозиторий "{self.repository_owner}/{self.repository_name}".')
        # Переписать логику
        self.return_json = {
            'queryInfo': {
                'code': 404,
                'error': 'Repository not found',
                # 'type': self.data['errors'][0]['type'],
                'message': self.data['errors'][0]['message'],
            },
        }
