<?php
$credentials = json_decode(file_get_contents('/run/secrets/credentials'), true);
add_role('labo_agent', 'MCP実験ユーザー', ['read' => true, 'edit_posts' => true]);
foreach (['labo_agent' => 'labo_agent', 'labo_reader' => 'subscriber'] as $login => $role) {
    $user = get_user_by('login', $login);
    $id = $user ? $user->ID : wp_insert_user([
        'user_login' => $login, 'user_pass' => $credentials['subscriber_password'],
        'user_email' => $login . '@example.invalid', 'role' => $role,
    ]);
    $password = WP_Application_Passwords::create_new_application_password($id, ['name' => 'Lilting MCP experiment']);
    if (is_wp_error($password)) { throw new Exception($password->get_error_message()); }
    $result[$login] = ['user_id' => $id, 'application_password' => $password[0]];
}
$fixture = get_page_by_path('labo-repair-cafe', OBJECT, 'post');
$post_id = $fixture ? $fixture->ID : wp_insert_post([
    'post_title' => '図書館の秋の修理カフェ', 'post_name' => 'labo-repair-cafe',
    'post_content' => file_get_contents('/labo-fixtures/article.txt'),
    'post_status' => 'publish', 'post_author' => 1,
    'meta_input' => ['_labo_fixture' => '1'],
]);
$result['fixture_post_id'] = $post_id;
echo wp_json_encode($result, JSON_UNESCAPED_UNICODE);
